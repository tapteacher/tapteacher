import smtplib
from django.core.management.base import BaseCommand
from core.models import VacancyPost, UserVerification, Vacancy
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import json
import random

class Command(BaseCommand):
    help = 'Sends daily job alerts (max 499).'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Job Alerts Script...")
        
        # 1. Fetch New Vacancies
        # User requested: 10 minute buffer before sending alerts
        time_threshold = timezone.now() - timedelta(minutes=10)
        
        new_posts = VacancyPost.objects.filter(
            vacancy__created_at__lte=time_threshold,
            vacancy__is_active=True,
            alert_emails_sent=False
        ).select_related('vacancy', 'vacancy__institute')
        
        if not new_posts.exists():
            self.stdout.write("No eligible vacancies found.")
            return

        self.stdout.write(f"Found {new_posts.count()} new posts to process.")

        # 2. Match Users
        # Map: user_id -> [list of matched post objects]
        user_matches = {}
        all_verifications = UserVerification.objects.prefetch_related('viewed_vacancies', 'user')

        for post in new_posts:
            post_state = post.vacancy.institute.state.lower().strip()
            post_district = post.vacancy.institute.district.lower().strip()
            post_category = post.category.lower().strip()
            post_subject = post.subject.lower().strip()

            for verif in all_verifications:
                prefs = verif.location_preferences or []
                match_found = False
                
                # Check preferences
                for pref in prefs:
                    pref_state = pref.get('state', '').lower().strip()
                    pref_district = pref.get('district', '').lower().strip()
                    if pref_state == post_state and pref_district == post_district:
                        subjects_dict = pref.get('subjects', {})
                        # The database keys are exactly 'PRT', 'TGT', 'PGT', 'Others'
                        # but post_category from VacancyPost might be lowercase depending on creation
                        # Let's do a case-insensitive lookup
                        for saved_cat, saved_subjects in subjects_dict.items():
                            if saved_cat.lower().strip() == post_category:
                                subjects_list = [s.lower().strip() for s in saved_subjects]
                                if post_subject in subjects_list:
                                    match_found = True
                                    break
                        if match_found:
                            break
                
                if match_found:
                    # SMART FILTER: Have they already viewed it organically?
                    if not verif.viewed_vacancies.filter(id=post.id).exists():
                        if verif.user.id not in user_matches:
                            user_matches[verif.user.id] = []
                        user_matches[verif.user.id].append(post)

        if not user_matches:
            self.stdout.write("No matching users found.")
            # Mark posts as processed so we don't try again
            new_posts.update(alert_emails_sent=True)
            return

        self.stdout.write(f"Matched {len(user_matches)} total users.")

        # 3. The 499 Filter Algorithm
        users_list = []
        for uid, posts in user_matches.items():
            verif = UserVerification.objects.get(user__id=uid)
            users_list.append((uid, verif.alert_engagement_score, posts, verif.user))

        loyalists = [u for u in users_list if u[1] > 0]
        newcomers = [u for u in users_list if u[1] == 0]

        loyalists.sort(key=lambda x: x[1], reverse=True)
        random.shuffle(newcomers)

        MAX_QUOTA = 499
        final_list = []

        if len(loyalists) >= 350:
            final_list.extend(loyalists[:350])
            remaining_quota = MAX_QUOTA - 350
            final_list.extend(newcomers[:remaining_quota])
        else:
            final_list.extend(loyalists)
            remaining_quota = MAX_QUOTA - len(loyalists)
            final_list.extend(newcomers[:remaining_quota])

        final_list = final_list[:MAX_QUOTA]

        self.stdout.write(f"Sending emails to {len(final_list)} users after 499 cutoff limit.")

        # 4. Dispatch Emails
        from_email = getattr(settings, 'EMAIL_HOST_USER', 'tapteacher.in@gmail.com')
        success_count = 0

        for user_data in final_list:
            uid, score, matched_posts, user = user_data
            
            context = {
                'user_name': user.first_name or user.username,
                'matched_posts': matched_posts,
                'domain': 'https://tapteacher.in' if not settings.DEBUG else 'http://127.0.0.1:8000'
            }
            
            html_content = render_to_string('core/emails/daily_job_alert.html', context)
            text_content = f"Hi {context['user_name']},\n\nWe found {len(matched_posts)} new teaching vacancies matching your exact location preferences on TapTeacher. Log in today to apply!"
            
            if len(matched_posts) == 1:
                subject = f"New Vacancy Match! 🎯 {matched_posts[0].subject.title()} Teacher in {matched_posts[0].vacancy.institute.district.title()}"
            else:
                subject = f"{len(matched_posts)} New Vacancy Matches just for you! 🎯"

            import os
            import requests
            api_key = os.environ.get('BREVO_API_KEY')
            
            if api_key:
                # Send via Brevo HTTP API
                url = "https://api.brevo.com/v3/smtp/email"
                headers = {
                    "accept": "application/json",
                    "api-key": api_key,
                    "content-type": "application/json"
                }
                payload = {
                    "sender": {
                        "name": "TapTeacher Alerts",
                        "email": from_email
                    },
                    "to": [
                        {
                            "email": user.email
                        }
                    ],
                    "subject": subject,
                    "htmlContent": html_content,
                    "textContent": text_content
                }
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    if response.status_code in [200, 201, 202]:
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"Brevo API error for {user.email}: Status {response.status_code}, Response: {response.text}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send to {user.email} via Brevo: {e}"))
            else:
                # Fallback to local Django SMTP
                msg = EmailMultiAlternatives(subject, text_content, f"TapTeacher Alerts <{from_email}>", [user.email])
                msg.attach_alternative(html_content, "text/html")
                try:
                    msg.send()
                    success_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send to {user.email}: {e}"))

        new_posts.update(alert_emails_sent=True)
        self.stdout.write(self.style.SUCCESS(f"Successfully sent {success_count} emails."))
