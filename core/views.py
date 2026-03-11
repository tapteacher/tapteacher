from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .data import INDIA_DATA
from .models import SiteSettings, UserReadVacancy
from django.utils import timezone
from datetime import timedelta
import json

def home(request):
    category = request.GET.get('category', 'govt') # Default to government
    
    category_titles = {
        'govt': 'Government School Vacancy',
        'semi': 'Semi-Government School Vacancy',
        'private': 'Private School Vacancy',
        'coaching': 'Private Coaching & Tution Vacancy'
    }
    
    current_title = category_titles.get(category, 'Government School Vacancy')

    states = sorted(list(INDIA_DATA.keys()))
    
    # --- Automated Cleaning: Expire vacancies older than 10 days (User Side Trigger) ---
    # This ensures that even if Admin doesn't log in, the user sees up-to-date data.
    from .models import Vacancy
    cutoff = timezone.now() - timedelta(days=10)
    Vacancy.objects.filter(is_active=True, created_at__lt=cutoff).update(is_active=False)
    # ---------------------------------------------------------------------------------
    
    # Blink Logic for States - Hierarchical
    # A state blinks if it contains ANY unacknowledged vacancy
    base_vacancies = Vacancy.objects.filter(
        institute__category=category,
        is_active=True,
        created_at__gt=cutoff
    )
    
    # For authenticated users, exclude acknowledged vacancies
    if request.user.is_authenticated:
        read_ids = get_user_read_ids(request.user)
        base_vacancies = base_vacancies.exclude(id__in=read_ids)
    
    # Get unique states with unacknowledged vacancies
    blinking_states = set(
        base_vacancies.values_list('institute__state', flat=True).distinct()
    )
    
    return render(request, 'core/home.html', {
        'states': states,
        'current_category': category,
        'current_title': current_title,
        'blinking_states': blinking_states
    })

def state_view(request, state_name):
    category = request.GET.get('category', 'govt')
    
    category_titles = {
        'govt': 'Government School Vacancy',
        'semi': 'Semi-Government School Vacancy',
        'private': 'Private School Vacancy',
        'coaching': 'Private Coaching & Tution Vacancy'
    }
    
    category_title = category_titles.get(category, 'Government School Vacancy')
    page_title = f"{category_title} in {state_name}"

    # Blinking Districts Logic - Hierarchical
    # A district blinks if it contains ANY unacknowledged vacancy
    ten_days_ago = timezone.now() - timedelta(days=10)
    
    base_vacancies = Vacancy.objects.filter(
        institute__state=state_name,
        institute__category__iexact=category,
        is_active=True,
        created_at__gte=ten_days_ago
    )
    
    # For authenticated users, exclude acknowledged vacancies
    if request.user.is_authenticated:
        read_ids = get_user_read_ids(request.user)
        base_vacancies = base_vacancies.exclude(id__in=read_ids)
    
    # Get unique districts with unacknowledged vacancies
    blinking_districts = set(
        base_vacancies.values_list('institute__district', flat=True).distinct()
    )

    # Fetch districts from INDIA_DATA
    districts = sorted(INDIA_DATA.get(state_name, []))
    
    return render(request, 'core/state_detail.html', {
        'state_name': state_name,
        'current_category': category,
        'page_title': page_title,
        'districts': districts, # Pass district names
        'blinking_districts': blinking_districts
    })

def district_view(request, state_name, district_name):
    category = request.GET.get('category', 'govt')
    
    # Query database for institutes
    from django.db.models import Exists, OuterRef
    
    # Note: Auto-expiration handles the 10-day rule for "active" vacancies.
    # So if it's active, it's new.
    vacancies = Vacancy.objects.filter(
        institute__state=state_name,
        institute__district=district_name,
        institute__category=category,
        is_active=True
    ).select_related('institute').order_by('-created_at') # Sort: Newest first (created_at) or Posted Date?
    # Usually created_at is better for "New".
    
    # School-Level Grouping and Blinking Logic
    # Key: A school blinks if ANY of its vacancies are unacknowledged
    # A school stops blinking only when ALL its vacancies are acknowledged
    
    from collections import defaultdict
    
    # Group vacancies by school (institute name)
    schools = defaultdict(list)
    for v in vacancies:
        schools[v.institute.name].append(v)
    
    # Get user's acknowledged vacancy IDs
    user_read_ids = set()
    if request.user.is_authenticated:
        user_read_ids = set(get_user_read_ids(request.user))
    
    # Define cutoff for "new" vacancies (within 10 days)
    ten_days_ago = timezone.now() - timedelta(days=10)
    
    # Build formatted list with school-level blink status
    formatted_vacancies = []
    for school_name, school_vacancies in schools.items():
        # Get the most recent vacancy for display info
        first_vacancy = school_vacancies[0]  # Already sorted by -created_at
        
        # Collect all vacancy IDs for this school
        school_vacancy_ids = {v.id for v in school_vacancies}
        
        # Check if ALL vacancies for this school are acknowledged
        all_acknowledged = school_vacancy_ids.issubset(user_read_ids)
        
        # School blinks if:
        # 1. It has new vacancies (within 10 days), AND
        # 2. NOT all vacancies are acknowledged
        is_blinking = False
        if first_vacancy.created_at >= ten_days_ago:
            if request.user.is_authenticated:
                is_blinking = not all_acknowledged
            else:
                # Guest - always blink initially (JS will handle local storage)
                is_blinking = True
        
        formatted_vacancies.append({
            'id': first_vacancy.id,  # Representative ID for toggle endpoint
            'title': school_name,
            'posted_date': first_vacancy.created_at.strftime('%d/%m/%Y'),
            'is_blinking': is_blinking,
            'vacancy_count': len(school_vacancies)  # For debugging/display
        })
    
    # Sort by posted date (newest first)
    formatted_vacancies.sort(key=lambda x: x['posted_date'], reverse=True)
    
    category_titles = {
        'govt': 'Government School Vacancy',
        'semi': 'Semi-Government School Vacancy',
        'private': 'Private School Vacancy',
        'coaching': 'Private Coaching & Tution Vacancy'
    }
    category_title = category_titles.get(category, 'Government School Vacancy')
    page_title = f"{category_title} in {district_name}, {state_name}"

    return render(request, 'core/district_detail.html', {
        'state_name': state_name,
        'district_name': district_name,
        'current_category': category,
        'page_title': page_title,
        'vacancies': formatted_vacancies
    })

def institute_view(request, state_name, district_name, institute_name):
    category = request.GET.get('category', 'govt')
    vacancy_type = request.GET.get('type')  # e.g., 'prt', 'tgt', 'pgt', 'other'
    
    # Fetch real institute
    institute = Institute.objects.filter(
        name=institute_name,
        state=state_name,
        district=district_name
    ).first()

    if not institute:
        # Fallback
        belief = "Our mission is to provide quality education and foster a learning environment that empowers students to achieve their full potential."
        prt_list = []
        tgt_list = []
        pgt_list = []
        other_list = []
        subjects = []
    else:
        belief = institute.belief or "No belief statement provided."
        # Get latest vacancy for this institute that is active
        latest_vacancy = institute.vacancies.filter(is_active=True).order_by('-created_at').first()
        
        prt_list = []
        tgt_list = []
        pgt_list = []
        other_list = []
        subjects = []

        if latest_vacancy:
            # Group posts
            # Get IDs of posts the user has already applied to or marked not interested
            excluded_post_ids = []
            if request.user.is_authenticated:
                excluded_post_ids = UserApplication.objects.filter(
                    user=request.user, 
                    status__in=['applied', 'not_interested']
                ).values_list('vacancy_post_id', flat=True)

            posts = latest_vacancy.posts.all()
            for p in posts:
                # Skip if user applied or is not interested
                if p.id in excluded_post_ids:
                    continue

                item = {'name': p.subject}
                if p.category == 'prt': prt_list.append(item)
                elif p.category == 'tgt': tgt_list.append(item)
                elif p.category == 'pgt': pgt_list.append(item)
                else: other_list.append(item)
            
            # If a specific type is selected, filter subjects for that type
            if vacancy_type:
                # We need to re-filter specifically for the selected type's subjects list
                filtered_posts = posts.filter(category=vacancy_type).exclude(id__in=excluded_post_ids)
                subjects = [p.subject for p in filtered_posts]
                
    # New: if user is viewing specific type, pass mailto links for subjects?
    # Actually, institute_view lists subjects. The "Apply" usually happens on vacancy_detail or some apply action.
    # But if there are "Apply" buttons next to subjects in the list (if that's the UI):
    # The UI currently seems to just list subjects.
    # Let's assume standard flow goes to vacancy_detail_view for a specific post.
    # However, if we want to pass a generic mailto for the institute?
    # The user said "when user applied in the vacancy of tgt physics".
    
    return render(request, 'core/institute_detail.html', {
        'state_name': state_name,
        'district_name': district_name,
        'institute_name': institute_name,
        'current_category': category,
        'belief': belief,
        'prt_list': prt_list,
        'tgt_list': tgt_list,
        'pgt_list': pgt_list,
        'other_list': other_list,
        'selected_type': vacancy_type,
        'subjects': subjects,
        'images': institute.images.all() if institute else []
    })

def vacancy_detail_view(request, state_name, district_name, institute_name, subject_name):
    category = request.GET.get('category', 'govt')
    vacancy_type = request.GET.get('type', 'other') # Default to other if not specified

    # Fetch specific post
    post = VacancyPost.objects.filter(
        vacancy__institute__name=institute_name,
        vacancy__institute__state=state_name,
        vacancy__institute__district=district_name,
        category=vacancy_type.strip().lower(),
        subject=subject_name.strip().lower()
    ).order_by('-vacancy__created_at').first()

    if post:
        qualification = post.qualification
        compensation = post.compensation
        eligibility = post.eligibility
        age_limit = post.age_limit
        app_link = post.vacancy.application_link
        post_id = post.id
    else:
        # Fallback for mock data
        qualification = "NA"
        compensation = "NA"
        eligibility = "NA"
        age_limit = "NA"
        app_link = "#"
        post_id = None

    # Category display name
    category_titles = {
        'govt': 'Government',
        'semi': 'Semi-Government',
        'private': 'Private',
        'coaching': 'Coaching'
    }
    category_title = category_titles.get(category, 'Other')
    vacancy_type_label = vacancy_type.upper()
    
    # Generate Mailto Link
    mailto_link = generate_mailto_link(request, vacancy_type, subject_name, app_link)

    return render(request, 'core/vacancy_detail.html', {
        'state_name': state_name,
        'district_name': district_name,
        'institute_name': institute_name,
        'subject_name': subject_name,
        'category_title': category_title,
        'vacancy_type_label': vacancy_type_label,
        'qualification': qualification,
        'compensation': compensation,
        'eligibility': eligibility,
        'age_limit': age_limit,
        'application_link': app_link,
        'post_id': post_id,
        'mailto_link': mailto_link
    })

def generate_mailto_link(request, category, subject, application_email=None):
    """
    Helper to generate a mailto link with pre-filled subject and body.
    Includes links to user's uploaded documents if authenticated.
    """
    from .models import EmailTemplate, UserVerification
    import urllib.parse
    
    # 1. Find Template
    template = EmailTemplate.objects.filter(
        category=category.strip().lower(), 
        subject=subject.strip().lower()
    ).first()
    
    email_subject = ""
    email_body = ""
    
    if template:
        email_subject = template.email_subject
        email_body = template.email_body
    else:
        # Fallback
        email_subject = f"Application for {subject} ({category.upper()})"
        email_body = f"Dear Principal/Hiring Manager,\n\nI am writing to apply for the position of {subject}.\n\n"
    
    # 2. Append User Profile Links if authenticated
    if request.user.is_authenticated:
        try:
            verification = request.user.verification
            domain = request.build_absolute_uri('/')[:-1] # Get domain e.g. http://127.0.0.1:8000
            
            docs_text = "\n\n--- My Documents ---\n"
            has_docs = False
            
            if verification.resume:
                docs_text += f"Resume: {domain}{verification.resume.url}\n"
                has_docs = True
            if verification.highest_qual_file:
                docs_text += f"Highest Qualification: {domain}{verification.highest_qual_file.url}\n"
                has_docs = True
            if verification.edu_cert_file:
                docs_text += f"Education Certificate: {domain}{verification.edu_cert_file.url}\n"
                has_docs = True
            if verification.exp_file:
                docs_text += f"Experience: {domain}{verification.exp_file.url}\n"
                has_docs = True
            if verification.salary_statement_file:
                docs_text += f"Salary Statement: {domain}{verification.salary_statement_file.url}\n"
                has_docs = True
                
            if has_docs:
                email_body += docs_text
        except UserVerification.DoesNotExist:
            pass
            
    # 3. Construct Mailto
    # mailto:email?subject=...&body=...
    recipient = application_email if application_email else ""
    
    # URL Encode
    params = {
        'subject': email_subject,
        'body': email_body
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    
    return f"mailto:{recipient}?{query_string}"

# Auth Views
def login_view(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        user = None
        # Try finding the user by email first
        if '@' in username_or_email:
            # Special Case: Admin Account First-Time Setup & Sync
            if username_or_email == "pankajyadav5501@gmail.com" and password == "Pankaj@123":
                admin_user, _ = User.objects.get_or_create(
                    email=username_or_email,
                    defaults={'username': username_or_email.split('@')[0]}
                )
                admin_user.set_password(password)
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.is_active = True
                admin_user.save()
                user = authenticate(request, username=admin_user.username, password=password)
            else:
                try:
                    user_found = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_found.username, password=password)
                except User.DoesNotExist:
                    pass
        
        # Fallback to direct username authentication
        if not user:
            user = authenticate(request, username=username_or_email, password=password)
            
        if user is not None:
            # Special check for the requested admin account to ensure it's always superuser
            if user.email == "pankajyadav5501@gmail.com":
                if not user.is_staff or not user.is_superuser:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

            login(request, user)
            request.session.set_expiry(1209600)  # 2 weeks
            return redirect('admin_dashboard' if user.is_staff else 'user_dashboard')
        else:
            return render(request, 'core/login.html', {
                'error': 'Invalid credentials',
                'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID
            })
            
    return render(request, 'core/login.html', {
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID
    })

@csrf_exempt
def google_login_callback(request):
    if request.method == 'POST':
        token = request.POST.get('credential')
        if not token:
            return redirect('login_view')

        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            
            # Fetch only Gmail ID (email)
            email = idinfo['email']
            
            # Get or create user
            user, created = User.objects.get_or_create(email=email, defaults={'username': email.split('@')[0]})
            
            # Special case for the admin email
            if email == "pankajyadav5501@gmail.com":
                user.is_staff = True
                user.is_superuser = True
                user.save()

            login(request, user)
            # Ensure persistent session
            request.session.set_expiry(1209600) # 2 weeks
            
            return redirect('user_dashboard' if not user.is_staff else 'admin_dashboard')
        except ValueError:
            # Invalid token
            return render(request, 'core/login.html', {'error': 'Invalid Google account'})

    return redirect('login_view')

from .models import SiteSettings, Institute, Vacancy, VacancyPost, InstituteImage, UserApplication
from .data import INDIA_DATA
from django.http import JsonResponse
from django.db.models import Count, Q

@login_required(login_url='login_view')
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')

    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create()
    
    # --- Automated Cleaning: Expire vacancies older than 10 days ---
    cutoff_date = timezone.now() - timedelta(days=10)
    # Perform soft-delete (is_active=False) on old active vacancies
    # We filter by is_active=True to avoid re-updating already inactive ones
    expired_count = Vacancy.objects.filter(is_active=True, created_at__lt=cutoff_date).update(is_active=False)
    # Optional: Log or print expired_count if debugging needed
    # -------------------------------------------------------------

    # Fetch Email Templates for display
    from .models import EmailTemplate
    email_templates = EmailTemplate.objects.all().order_by('category', 'subject')

    # Fetch Submitted Vacancies - Only active ones, annotated with applicant count
    submitted_vacancies = Vacancy.objects.filter(is_active=True).annotate(
        total_applicants=Count('posts__applications', filter=Q(posts__applications__status='applied'))
    ).order_by('-created_at').select_related('institute')
    
    # Calculate detailed post stats
    # We want something like: "Mathematics (PGT): 5 posts" or just "Total PGT: 10"
    # User asked for: "subject wise the total vacancy will shown"
    
    # Logic removed as per user request
    # subject_stats = VacancyPost.objects.values('subject').annotate(total=Count('id')).order_by('-total')

    if request.method == 'POST':
        # Handle "Manage connect link" update
        if 'update_links' in request.POST:
            settings.youtube_link = request.POST.get('youtube_link', '')
            settings.telegram_link = request.POST.get('telegram_link', '')
            settings.save()
            # Success logic...
        
        # Handle "Upload Vacancy" submission
        elif 'upload_vacancy' in request.POST:
            institute_name = request.POST.get('institute_name')
            category = request.POST.get('institute_category')
            state = request.POST.get('state')
            district = request.POST.get('district')
            belief = request.POST.get('belief', '')
            app_link = request.POST.get('application_link')

            # Create or update Institute
            institute, _ = Institute.objects.get_or_create(
                name=institute_name,
                state=state,
                district=district,
                defaults={'category': category, 'belief': belief}
            )
            # Update fields if it already existed
            if not _:
                institute.category = category
                institute.belief = belief
                institute.save()

            # Handle photo uploads
            if request.FILES.getlist('photos'):
                for photo in request.FILES.getlist('photos'):
                    InstituteImage.objects.create(institute=institute, image=photo)

            # Create Vacancy
            vacancy = Vacancy.objects.create(
                institute=institute,
                application_link=app_link
            )

            # Create Posts
            categories = request.POST.getlist('post_category[]')
            subjects = request.POST.getlist('post_subject[]')
            qualifications = request.POST.getlist('post_qualification[]')
            compensations = request.POST.getlist('post_compensation[]')
            eligibilities = request.POST.getlist('post_eligibility[]')
            age_limits = request.POST.getlist('post_age_limit[]')

            for i in range(len(categories)):
                VacancyPost.objects.create(
                    vacancy=vacancy,
                    category=categories[i].strip(),
                    subject=subjects[i].strip(),
                    qualification=qualifications[i] if i < len(qualifications) else "NA",
                    compensation=compensations[i] if i < len(compensations) else "NA",
                    eligibility=eligibilities[i] if i < len(eligibilities) else "NA",
                    age_limit=age_limits[i] if i < len(age_limits) else "NA"
                )
            
            # In a real app we'd redirect with a success message
            return redirect('admin_dashboard')

        # Handle "Upload Syllabus" submission
        elif 'upload_syllabus' in request.POST:
            from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic, GuidanceTopicFile, User
            
            target_audience = request.POST.get('target_audience')
            category_slug = request.POST.get('guidance_category')
            subject_name = request.POST.get('subject_name')
            
            # Find or Create Category
            if category_slug:
                category, _ = GuidanceCategory.objects.get_or_create(slug=category_slug, defaults={'name': category_slug.upper()})
                
                # Find or Create Subject
                subject, _ = GuidanceSubject.objects.get_or_create(
                    category=category, 
                    name=subject_name
                )
                
                # Handle Topics
                topic_limit = int(request.POST.get('topic_count', 0))
                
                assigned_user = None
                assigned_user = None
                if target_audience == 'individual':
                    user_id = request.POST.get('selected_user_id')
                    try:
                        if user_id:
                            assigned_user = User.objects.get(id=user_id)
                        else:
                             # Fallback or Error
                             from django.contrib import messages
                             messages.error(request, "Please select a user for Individual Syllabus.")
                             return redirect('admin_dashboard')
                    except User.DoesNotExist:
                        from django.contrib import messages
                        messages.error(request, "Selected user does not exist.")
                        return redirect('admin_dashboard')
                
                # Loop through potential topics
                # Note: topicCounter in JS increments, so we iterate up to the limit
                # But since we might have deleted some? 
                # Actually my JS implementation doesn't support deleting topics yet for simplicitly, 
                # but valid indices are 0 to topic_limit-1.
                
                for i in range(topic_limit):
                    title = request.POST.get(f'topic_title_{i}')
                    if not title: 
                        continue # Skip empty or missing
                    
                    desc = request.POST.get(f'topic_desc_{i}', '')
                    
                    # Create Topic
                    topic = GuidanceTopic.objects.create(
                        subject=subject,
                        title=title,
                        description=desc,
                        is_for_everyone=(target_audience == 'everyone')
                    )
                    
                    if assigned_user:
                        topic.assigned_users.add(assigned_user)
                    
                    topic.save()

                    # Handle Multiple Files
                    # PPTs
                    if request.FILES.getlist(f'topic_ppt_{i}[]'):
                        for f in request.FILES.getlist(f'topic_ppt_{i}[]'):
                            GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='ppt')
                    
                    # PDFs
                    if request.FILES.getlist(f'topic_pdf_{i}[]'):
                        for f in request.FILES.getlist(f'topic_pdf_{i}[]'):
                            GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='pdf')

                    # Images
                    if request.FILES.getlist(f'topic_image_{i}[]'):
                        for f in request.FILES.getlist(f'topic_image_{i}[]'):
                            GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='image')
            
            return redirect('admin_dashboard')
            
        # Handle "Add/Edit Email Template"
        elif 'save_email_template' in request.POST:
            from .models import EmailTemplate
            cat = request.POST.get('template_category', '').strip()
            sub = request.POST.get('template_subject', '').strip()
            
            # Simple upsert based on category + subject
            template, created = EmailTemplate.objects.get_or_create(
                category=cat,
                subject=sub,
                defaults={
                    'email_subject': request.POST.get('email_subject'),
                    'email_body': request.POST.get('email_body')
                }
            )
            if not created:
                template.email_subject = request.POST.get('email_subject')
                template.email_body = request.POST.get('email_body')
                template.save()
            return redirect('admin_dashboard')
            
        # Handle "Delete Email Template"
        elif 'delete_email_template' in request.POST:
            from .models import EmailTemplate
            t_id = request.POST.get('template_id')
            EmailTemplate.objects.filter(id=t_id).delete()
            return redirect('admin_dashboard')

    return render(request, 'core/admin_dashboard.html', {
        'settings': settings,
        'india_data': INDIA_DATA,
        'submitted_vacancies': submitted_vacancies,
        'email_templates': email_templates,
    })

@login_required(login_url='login_view')
def edit_vacancy(request, vacancy_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    posts = vacancy.posts.all()
    
    # We reuse the admin dashboard template logic or a specific edit template
    # For now, let's process the update here.
    
    if request.method == 'POST':
        # Reuse logic similar to upload but updating
        # For simplicity in this turn, I'll extract common update logic if possible, 
        # or just handle it directly here as the user asked for "Resubmit" which implies a new save.
        
        # User said: "previous one of that will be erase and new will then shown"
        # This strongly suggests we DELETE the old posts and recreate them, OR update in place.
        # Dropping and recreating posts is easier for sync if the counts change.
        
        institute_name = request.POST.get('institute_name')
        category = request.POST.get('institute_category')
        state = request.POST.get('state')
        district = request.POST.get('district')
        belief = request.POST.get('belief', '')
        app_link = request.POST.get('application_link')

        # Update Institute
        inst = vacancy.institute
        inst.name = institute_name
        inst.category = category
        inst.state = state
        inst.district = district
        inst.belief = belief
        inst.save()
        
        # Update Vacancy
        vacancy.application_link = app_link
        # "new will then shown" -> Update created_at to bump it to top?
        from django.utils import timezone
        vacancy.created_at = timezone.now()
        vacancy.save()
        
        # Update Posts: Delete all old posts and recreate from form
        vacancy.posts.all().delete()
        
        categories = request.POST.getlist('post_category[]')
        subjects = request.POST.getlist('post_subject[]')
        qualifications = request.POST.getlist('post_qualification[]')
        compensations = request.POST.getlist('post_compensation[]')
        eligibilities = request.POST.getlist('post_eligibility[]')
        age_limits = request.POST.getlist('post_age_limit[]')

        for i in range(len(categories)):
            VacancyPost.objects.create(
                vacancy=vacancy,
                category=categories[i].strip(),
                subject=subjects[i].strip(),
                qualification=qualifications[i] if i < len(qualifications) else "NA",
                compensation=compensations[i] if i < len(compensations) else "NA",
                eligibility=eligibilities[i] if i < len(eligibilities) else "NA",
                age_limit=age_limits[i] if i < len(age_limits) else "NA"
            )
            
        return redirect('admin_dashboard')

    return render(request, 'core/edit_vacancy.html', {
        'vacancy': vacancy,
        'posts': posts,
        'india_data': INDIA_DATA
    })

from django.contrib import messages

@login_required(login_url='login_view')
def delete_vacancy(request, vacancy_id):
    if not request.user.is_superuser:
        return redirect('home')
    
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    vacancy.is_active = False
    vacancy.save()
    
    # messages.success(request, f"Vacancy for '{vacancy.institute.name}' has been soft-deleted.")
    
    # Redirect back to admin dashboard
    return redirect('admin_dashboard')

@login_required(login_url='login_view')
def vacancy_applicants(request, vacancy_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    # Aggregate applicants from all posts in this vacancy
    # We want to list unique users per vacancy? Or list by post?
    # User said: "find the number of candidate who has applied in that post with thier line wise name"
    # "that post" might mean the Vacancy group.
    
    posts = vacancy.posts.all()
    # Let's group by Post
    
    applicants_data = []
    total_applicants = 0
    
    for post in posts:
        apps = UserApplication.objects.filter(vacancy_post=post, status='applied').select_related('user', 'user__verification')
        if apps.exists():
            applicants_data.append({
                'post': post,
                'applications': apps
            })
            total_applicants += apps.count()
            
    return render(request, 'core/vacancy_applicants.html', {
        'vacancy': vacancy,
        'applicants_data': applicants_data,
        'total_applicants': total_applicants
    })

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='login_view')
def user_dashboard(request, user_id=None):
    from .models import UserVerification
    
    # Admin Introspection Logic
    target_user = request.user
    is_admin_viewing = False
    
    if user_id and request.user.is_superuser:
        target_user = get_object_or_404(User, id=user_id)
        is_admin_viewing = True
    
    # Get or create verification profile for the TARGET user
    verification, created = UserVerification.objects.get_or_create(user=target_user)
    
    if request.method == 'POST':
        # Handle "Verification Details" submission
        if 'update_verification' in request.POST:
            verification.full_name = request.POST.get('full_name')
            verification.phone_number = request.POST.get('phone_number')
            verification.gender = request.POST.get('gender')
            
            dob_str = request.POST.get('dob')
            if dob_str:
                from datetime import datetime
                verification.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            
            verification.additional_email = request.POST.get('additional_email')
            verification.highest_qual_desc = request.POST.get('highest_qual_desc')
            verification.edu_cert_desc = request.POST.get('edu_cert_desc')
            verification.exp_desc = request.POST.get('exp_desc')
            verification.expected_salary = request.POST.get('expected_salary')
            
            # File Uploads
            if request.FILES.get('highest_qual_file'):
                verification.highest_qual_file = request.FILES['highest_qual_file']
            if request.FILES.get('edu_cert_file'):
                verification.edu_cert_file = request.FILES['edu_cert_file']
            if request.FILES.get('exp_file'):
                verification.exp_file = request.FILES['exp_file']
            if request.FILES.get('salary_statement_file'):
                verification.salary_statement_file = request.FILES['salary_statement_file']
            if request.FILES.get('resume'):
                verification.resume = request.FILES['resume']
                
            verification.save()
            # Refresh from database to ensure we have the latest data
            verification.refresh_from_db()
            
            # Redirect to avoid resubmission - maintain admin view if applicable
            if is_admin_viewing:
                return redirect('user_dashboard_admin', user_id=target_user.id)
            return redirect('user_dashboard')

    # Get applied vacancies for TARGET user
    applied_apps = target_user.applications.filter(status='applied').select_related(
        'vacancy_post__vacancy__institute'
    ).order_by('-applied_at')
    
    # Get saved vacancies for TARGET user
    saved_apps = target_user.applications.filter(status='saved').select_related(
        'vacancy_post__vacancy__institute'
    ).order_by('-applied_at')
    
    applied_count = applied_apps.count()
    saved_count = saved_apps.count()

    # Get chat messages for the user
    from .models import ChatMessage
    user_messages = ChatMessage.objects.filter(user=target_user).order_by('created_at')
    
    # Calculate unread messages count for blinking logic
    # We NO LONGER auto-mark as read here. This allows the UI to blink.
    unread_chat_count = 0
    if not is_admin_viewing:
        unread_chat_count = ChatMessage.objects.filter(user=target_user, sender_is_admin=True, is_read=False).count()

    return render(request, 'core/user_dashboard_v3.html', {
        'applied_vacancies': applied_apps,
        'saved_vacancies': saved_apps,
        'verification': verification,
        'applied_count': applied_count,
        'saved_count': saved_count,
        'is_admin_viewing': is_admin_viewing,
        'target_user': target_user,
        'user_messages': user_messages,
        'unread_chat_count': unread_chat_count,
        'user_full_name': verification.full_name or target_user.email # Override header name
    })

def apply_to_vacancy(request, post_id):
    from .models import VacancyPost, UserApplication
    from django.http import JsonResponse
    from django.utils import timezone
    
    if request.method == 'POST':
        # Guest User Logic
        if not request.user.is_authenticated:
            return JsonResponse({'success': True, 'message': 'Guest application - not saved'})

        try:
            vacancy_post = VacancyPost.objects.get(id=post_id)
            # Create or update application
            app, created = UserApplication.objects.get_or_create(
                user=request.user,
                vacancy_post=vacancy_post,
                defaults={'status': 'applied'}
            )
            # Update status (do not update timestamp to preserve original date)
            app.status = 'applied'
            # app.applied_at = timezone.now() -- Removed to fix date issue
            app.save()
                
            return JsonResponse({'success': True, 'message': 'Application saved!'})
        except VacancyPost.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Vacancy not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def save_for_later(request, post_id):
    from .models import VacancyPost, UserApplication
    from django.http import JsonResponse
    from django.utils import timezone
    
    if request.method == 'POST':
        # Guest User Logic
        if not request.user.is_authenticated:
            return JsonResponse({'success': True, 'message': 'Guest user - not saved'})

        try:
            vacancy_post = VacancyPost.objects.get(id=post_id)
            # Create or update saved application
            app, created = UserApplication.objects.get_or_create(
                user=request.user,
                vacancy_post=vacancy_post,
                defaults={'status': 'saved'}
            )
            # Update status (do not update timestamp to preserve original date)
            app.status = 'saved'
            # app.applied_at = timezone.now() -- Removed to fix date issue
            app.save()

            return JsonResponse({'success': True, 'message': 'Vacancy saved!'})
        except VacancyPost.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Vacancy not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def mark_not_interested(request, post_id):
    from .models import VacancyPost, UserApplication
    from django.http import JsonResponse
    
    if request.method == 'POST':
        # Guest User Logic
        if not request.user.is_authenticated:
            return JsonResponse({'success': True, 'message': 'Guest user - request acknowledged'})

        try:
            vacancy_post = VacancyPost.objects.get(id=post_id)
            # Mark as not interested
            app, created = UserApplication.objects.get_or_create(
                user=request.user,
                vacancy_post=vacancy_post,
                defaults={'status': 'not_interested'}
            )
            # If already existed, update - no need to update timestamp for not_interested usually, but fine
            app.status = 'not_interested'
            app.save()
                
            return JsonResponse({'success': True, 'message': 'Marked as not interested'})
        except VacancyPost.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Vacancy not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required(login_url='login_view')
def get_vacancy_details(request):
    """
    API to fetch qualification, compensation, eligibility, age_limit 
    from the latest post of a given institute and category.
    """
    if request.method == 'GET':
        institute_name = request.GET.get('institute_name')
        category = request.GET.get('post_category')
        
        if not institute_name or not category:
            return JsonResponse({'success': False})

        # Find latest post for this institute + category
        latest_post = VacancyPost.objects.filter(
            vacancy__institute__name=institute_name,
            category=category
        ).order_by('-vacancy__created_at').first()

        if latest_post:
            return JsonResponse({
                'success': True,
                'qualification': latest_post.qualification,
                'compensation': latest_post.compensation,
                'eligibility': latest_post.eligibility,
                'age_limit': latest_post.age_limit
            })
    
    return JsonResponse({'success': False})

@login_required(login_url='login_view')
def search_users(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'success': False, 'users': []})

    from django.db.models import Q
    from django.contrib.auth.models import User
    
    users = User.objects.filter(
        Q(email__icontains=query) | Q(username__icontains=query)
    ).values('id', 'username', 'email')[:10]
    
    return JsonResponse({'success': True, 'users': list(users)})

@login_required(login_url='login_view')
def syllabus_landing(request):
    # Ensure default categories exist to prevent 404s on hardcoded links
    from .models import GuidanceCategory
    defaults = ['prt', 'tgt', 'pgt', 'other']
    for slug in defaults:
        GuidanceCategory.objects.get_or_create(slug=slug, defaults={'name': slug.upper() + ' Vacancy'})

    # Determine user's reference time
    last_visit = None
    if request.user.is_authenticated:
        try:
           last_visit = request.user.verification.last_syllabus_visit
        except:
           pass
    else:
        # Check cookie for guests
        visit_cookie = request.COOKIES.get('last_syllabus_visit')
        if visit_cookie:
            from django.utils.dateparse import parse_datetime
            last_visit = parse_datetime(visit_cookie)
            
    # If no last visit, default to 7 days ago safe cutoff
    from django.utils import timezone
    from datetime import timedelta
    if not last_visit:
        last_visit = timezone.now() - timedelta(days=7)

    # Check for new topics per category
    from .models import GuidanceTopic
    from django.db.models import Q
    
    # helper
    def check_cat_blink(cat_slug):
        q = GuidanceTopic.objects.filter(
            subject__category__slug=cat_slug,
            created_at__gt=last_visit
        )
        if request.user.is_authenticated:
             return q.filter(Q(is_for_everyone=True) | Q(assigned_users=request.user)).exists()
        return q.filter(is_for_everyone=True).exists()

    blink_flags = {
        'blink_prt': check_cat_blink('prt'),
        'blink_tgt': check_cat_blink('tgt'),
        'blink_pgt': check_cat_blink('pgt'),
        'blink_other': check_cat_blink('other'),
    }

    view_as_user = request.GET.get('view_as') if request.user.is_superuser else None
    
    # Merge blink flags into context
    context = {'view_as_user': view_as_user}
    context.update(blink_flags)
    
    return render(request, 'core/syllabus_landing.html', context)

@login_required(login_url='login_view')
def syllabus_category_view(request, category_slug):
    # Update Last Visit Logic Here (Stop Blinking after visiting category)
    response = None
    if request.user.is_authenticated and not request.GET.get('view_as'):
        try:
            from django.utils import timezone
            v = request.user.verification
            v.last_syllabus_visit = timezone.now()
            v.save()
        except:
            pass
            
    from .models import GuidanceCategory, GuidanceSubject
    from django.shortcuts import get_object_or_404
    
    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    
    # efficiency: prefetch
    subjects = GuidanceSubject.objects.filter(category=category).prefetch_related('topics')

    view_as_id = request.GET.get('view_as')
    target_user_id = request.user.id
    if request.user.is_superuser and view_as_id:
        try:
            target_user_id = int(view_as_id)
        except ValueError:
            pass
    
    # Filter Logic:
    # Show subject if it has ANY topic visible to the user.
    visible_subjects = []
    for sub in subjects:
        # Check topics visibility
        topics = sub.topics.all()
        has_visible = False
        for t in topics:
            if t.is_for_everyone:
                has_visible = True
                break
            # Check visibility for target user (or superuser if not simulating)
            if t.assigned_users.filter(id=target_user_id).exists():
                has_visible = True
                break
            # If standard superuser view (no view_as), show everything?
            # User request implies they want to see user's perspective when "view_as" is set.
            # If no view_as, superuser should probably see all.
            if request.user.is_superuser and not view_as_id:
                has_visible = True
                break
        
        if has_visible:
            visible_subjects.append(sub)

    return render(request, 'core/syllabus_subjects.html', {
        'category': category,
        'subjects': visible_subjects,
        'view_as_user': view_as_id if request.user.is_superuser else None
    })

@login_required(login_url='login_view')
def syllabus_subject_view(request, category_slug, subject_id):
    from .models import GuidanceCategory, GuidanceSubject
    from django.shortcuts import get_object_or_404
    
    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    subject = get_object_or_404(GuidanceSubject, id=subject_id, category=category)
    
    view_as_id = request.GET.get('view_as')
    target_user_id = request.user.id
    if request.user.is_superuser and view_as_id:
        try:
            target_user_id = int(view_as_id)
        except ValueError:
            pass

    all_topics = subject.topics.all()
    visible_topics = []
    
    for t in all_topics:
        is_visible = False
        if request.user.is_superuser and not view_as_id:
            is_visible = True
        elif t.is_for_everyone:
            is_visible = True
        elif t.assigned_users.filter(id=target_user_id).exists():
            is_visible = True
        
        if is_visible:
            visible_topics.append(t)
            
    return render(request, 'core/syllabus_topics.html', {
        'category': category,
        'subject': subject,
        'topics': visible_topics,
        'view_as_user': view_as_id if request.user.is_superuser else None
    })

@login_required(login_url='login_view')
def syllabus_topic_detail_view(request, category_slug, subject_id, topic_id):
    from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic
    from django.shortcuts import get_object_or_404
    
    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    subject = get_object_or_404(GuidanceSubject, id=subject_id, category=category)
    topic = get_object_or_404(GuidanceTopic, id=topic_id, subject=subject)
    
    # Check access permission
    has_access = False
    if request.user.is_superuser:
        has_access = True
    elif topic.is_for_everyone:
        has_access = True
    elif request.user.is_authenticated and topic.assigned_users.filter(id=request.user.id).exists():
        has_access = True
        
    if not has_access:
        # Simplistic access denied handling
        return render(request, 'core/syllabus_topics.html', {
            'category': category, 
            'subject': subject,
            'topics': [], # Hide content
            'error_message': 'You do not have permission to view this topic.'
        })

    return render(request, 'core/syllabus_topic_detail.html', {
        'category': category,
        'subject': subject,
        'topic': topic,
        'view_as_user': request.GET.get('view_as') if request.user.is_superuser else None
    })


# ============ CHAT VIEWS ============

@login_required(login_url='login_view')
def user_chat_list(request):
    """Admin view: List all users with chat messages"""
    if not request.user.is_superuser:
        return redirect('home')
    
    from .models import ChatMessage
    users_with_chats = ChatMessage.get_users_with_messages()
    
    return render(request, 'core/admin_chat_list.html', {
        'users_with_chats': users_with_chats
    })


@login_required(login_url='login_view')
def user_chat_detail(request, user_id):
    """Admin view: Chat conversation with a specific user"""
    if not request.user.is_superuser:
        return redirect('home')
    
    from .models import ChatMessage
    chat_user = get_object_or_404(User, id=user_id)
    
    # Mark all messages from this user as read
    ChatMessage.objects.filter(user=chat_user, sender_is_admin=False, is_read=False).update(is_read=True)
    
    # Get all messages for this user
    messages = ChatMessage.objects.filter(user=chat_user).order_by('created_at')
    
    # Fetch Email Templates for "Email User" helper
    from .models import EmailTemplate
    email_templates = EmailTemplate.objects.all().order_by('category', 'subject')

    return render(request, 'core/admin_chat_detail.html', {
        'chat_user': chat_user,
        'messages': messages,
        'email_templates': email_templates,
    })


@login_required(login_url='login_view')
def admin_send_message(request, user_id):
    """Admin sends a message to a user"""
    if not request.user.is_superuser:
        return redirect('home')
    
    if request.method == 'POST':
        from .models import ChatMessage
        import os
        
        chat_user = get_object_or_404(User, id=user_id)
        message_text = request.POST.get('message_text', '').strip()
        attachment = request.FILES.get('attachment')
        
        # Validate that at least one of message or attachment is provided
        if not message_text and not attachment:
            from django.contrib import messages
            messages.error(request, "Please provide a message or attachment")
            return redirect('user_chat_detail', user_id=user_id)
        
        # Determine attachment type
        attachment_type = None
        if attachment:
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                attachment_type = 'image'
            elif ext == '.pdf':
                attachment_type = 'pdf'
            elif ext in ['.ppt', '.pptx']:
                attachment_type = 'ppt'
            else:
                attachment_type = 'other'
            
            # Validate file size (10MB max)
            if attachment.size > 10 * 1024 * 1024:
                from django.contrib import messages
                messages.error(request, "File size must be less than 10MB")
                return redirect('user_chat_detail', user_id=user_id)
        
        # Create message
        ChatMessage.objects.create(
            user=chat_user,
            sender_is_admin=True,
            message_text=message_text if message_text else None,
            attachment=attachment,
            attachment_type=attachment_type
        )
        
        from django.contrib import messages
        messages.success(request, "Message sent successfully")
    
    return redirect('user_chat_detail', user_id=user_id)


@login_required(login_url='login_view')
def user_send_message(request):
    """User sends a message to admin"""
    if request.method == 'POST':
        from .models import ChatMessage
        import os
        
        message_text = request.POST.get('message_text', '').strip()
        attachment = request.FILES.get('attachment')
        
        # Validate that at least one of message or attachment is provided
        if not message_text and not attachment:
            from django.contrib import messages
            messages.error(request, "Please provide a message or attachment")
            return redirect('user_dashboard')
        
        # Determine attachment type
        attachment_type = None
        if attachment:
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                attachment_type = 'image'
            elif ext == '.pdf':
                attachment_type = 'pdf'
            elif ext in ['.ppt', '.pptx']:
                attachment_type = 'ppt'
            else:
                attachment_type = 'other'
            
            # Validate file size (10MB max)
            if attachment.size > 10 * 1024 * 1024:
                from django.contrib import messages
                messages.error(request, "File size must be less than 10MB")
                return redirect('user_dashboard')
        
        # Create message
        ChatMessage.objects.create(
            user=request.user,
            sender_is_admin=False,
            message_text=message_text if message_text else None,
            attachment=attachment,
            attachment_type=attachment_type
        )
        
        # No success message as per user request to avoid redundancy
        # from django.contrib import messages
        # messages.success(request, "Message sent successfully")
    
    # Redirect to chat tab to avoid refresh issue
    return redirect('/user-dashboard/#chat')

@login_required(login_url='login_view')
def admin_user_list(request):
    """Admin view: List of all users for inspection"""
    if not request.user.is_superuser:
        return redirect('home')
    
    from django.db.models import Q
    from .models import UserVerification
    
    query = request.GET.get('q', '').strip()
    
    # Base queryset: All users (including admin/superuser for visibility if requested)
    users = User.objects.all().order_by('-date_joined')
    
    if query:
        # Search by Email or Unique Number
        # Unique number is in UserVerification model
        users = users.filter(
            Q(email__icontains=query) | 
            Q(verification__unique_number__icontains=query)
        ).distinct()
    
    user_list = []
    for u in users:
        # Get verification if exists
        try:
            profile = u.verification
        except UserVerification.DoesNotExist:
            profile = None
            
        user_list.append({
            'user': u,
            'profile': profile
        })
        
    return render(request, 'core/admin_user_list.html', {
        'user_list': user_list,
        'search_query': query
    })

@login_required(login_url='login_view')
def delete_topic(request, topic_id):
    if not request.user.is_superuser:
        return redirect('home')
    
    from .models import GuidanceTopic
    from django.contrib import messages
    
    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    
    # Store parent info for redirect
    subject_id = topic.subject.id
    category_slug = topic.subject.category.slug
    
    if request.method == 'POST':
        topic_title = topic.title
        topic.delete()
        messages.success(request, 'Topic deleted successfully.')
        
        # Construct redirect URL with view_as param if present
        from django.urls import reverse
        url = reverse('syllabus_subject', kwargs={'category_slug': category_slug, 'subject_id': subject_id})
        
        view_as = request.GET.get('view_as')
        if view_as:
            url += f'?view_as={view_as}'
            
        return redirect(url)
    
    # Fallback
    return redirect('syllabus_subject', category_slug=category_slug, subject_id=subject_id)

def get_user_read_ids(user):
    """Helper to get list of vacancy IDs a user has marked as read."""
    return list(UserReadVacancy.objects.filter(user=user).values_list('vacancy_id', flat=True))

@login_required(login_url='login_view')
def syllabus_topic_edit_view(request, category_slug, subject_id, topic_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic
    from django.shortcuts import get_object_or_404
    
    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    subject = get_object_or_404(GuidanceSubject, id=subject_id, category=category)
    topic = get_object_or_404(GuidanceTopic, id=topic_id, subject=subject)
    
    return render(request, 'core/syllabus_topic_edit.html', {
        'category': category,
        'subject': subject,
        'topic': topic,
        'view_as_user': request.GET.get('view_as') if request.user.is_superuser else None
    })


@login_required(login_url='login_view')
def edit_topic_inline(request, topic_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    from .models import GuidanceTopic
    from django.contrib import messages
    
    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    subject_id = topic.subject.id
    category_slug = topic.subject.category.slug
    
    if request.method == 'POST':
        new_title = request.POST.get('topic_title', '').strip()
        new_description = request.POST.get('topic_description', '').strip()
        
        if new_title:
            topic.title = new_title
            topic.description = new_description
            topic.save()
            messages.success(request, 'Topic updated successfully.')

            # Handle new image uploads
            from .models import GuidanceTopicFile
            new_images = request.FILES.getlist('new_images')
            for img in new_images:
                GuidanceTopicFile.objects.create(topic=topic, file=img, file_type='image')
        else:
            messages.error(request, 'Topic title cannot be empty.')
            
    from django.urls import reverse
    url = reverse('syllabus_topic_detail', kwargs={'category_slug': category_slug, 'subject_id': subject_id, 'topic_id': topic.id})
    view_as = request.GET.get('view_as')
    if view_as:
        url += f'?view_as={view_as}'
        
    return redirect(url)


@csrf_exempt
@login_required(login_url='login_view')
def delete_topic_file(request, file_id):
    """API to delete a GuidanceTopicFile record (used for broken image cleanup)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    from .models import GuidanceTopicFile
    import json
    
    if request.method == 'POST':
        try:
            file_obj = GuidanceTopicFile.objects.get(id=file_id)
            # Try to delete the actual file too (may fail on Cloudinary, that's ok)
            try:
                file_obj.file.delete(save=False)
            except Exception:
                pass
            file_obj.delete()
            return JsonResponse({'success': True})
        except GuidanceTopicFile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'File not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

@csrf_exempt
def toggle_vacancy_read(request, vacancy_id):
    """
    API to mark a school's vacancies as read or unread.
    
    School-Level Logic:
    - When user toggles a school, ALL vacancies for that school are affected
    - This ensures proper hierarchical blinking (school stops blinking only when ALL vacancies acknowledged)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
    
    if request.method == 'POST':
        try:
            from .models import Vacancy
            
            data = json.loads(request.body)
            action = data.get('action')  # 'mark_read' or 'mark_unread'
            
            # Get the vacancy to find its school
            try:
                vacancy = Vacancy.objects.select_related('institute').get(id=vacancy_id)
            except Vacancy.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Vacancy not found'}, status=404)
            
            # Get ALL active vacancies for this school (same institute name, state, district, category)
            school_vacancies = Vacancy.objects.filter(
                institute__name=vacancy.institute.name,
                institute__state=vacancy.institute.state,
                institute__district=vacancy.institute.district,
                institute__category=vacancy.institute.category,
                is_active=True
            )
            
            if action == 'mark_read':
                # Mark ALL school vacancies as read
                for v in school_vacancies:
                    UserReadVacancy.objects.get_or_create(
                        user=request.user,
                        vacancy_id=v.id
                    )
                return JsonResponse({
                    'success': True,
                    'message': f'Marked {school_vacancies.count()} vacancies as read'
                })
                
            elif action == 'mark_unread':
                # Remove ALL school vacancies from read list
                deleted_count = UserReadVacancy.objects.filter(
                    user=request.user,
                    vacancy_id__in=school_vacancies.values_list('id', flat=True)
                ).delete()[0]
                return JsonResponse({
                    'success': True,
                    'message': f'Unmarked {deleted_count} vacancies'
                })
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@login_required(login_url='login_view')
def mark_chat_read(request):
    """API to mark all admin messages as read for the current user"""
    if request.method == 'POST':
        from .models import ChatMessage
        from django.http import JsonResponse
        ChatMessage.objects.filter(user=request.user, sender_is_admin=True, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
