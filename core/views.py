from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
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
from django.contrib import messages

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
    )
    if request.user.is_authenticated and not request.user.is_superuser and hasattr(request.user, 'adminrole'):
        vacancies = vacancies.filter(uploaded_by=request.user)
    
    vacancies = vacancies.select_related('institute').order_by('-created_at')
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
    # HRs always see all vacancies for testing, skip exclusion
    is_hr_tester = request.user.is_authenticated and not request.user.is_superuser and hasattr(request.user, 'adminrole')
    
    if request.user.is_authenticated and not is_hr_tester:
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
        name=institute_name.strip(),
        state=state_name.strip(),
        district=district_name.strip()
    ).first()

    category_titles = {
        'govt': 'Government School',
        'semi': 'Semi-Government School',
        'private': 'Private School',
        'coaching': 'Private Coaching & Tuition'
    }
    category_title = category_titles.get(category, 'Other')

    if not institute:
        # Fallback
        belief = "Our mission is to provide quality education and foster a learning environment that empowers students to achieve their full potential."
        prt_list = []
        tgt_list = []
        pgt_list = []
        other_list = []
        categories = []
        subjects = []
        selected_type_display = ""
    else:
        belief = institute.belief or "No belief statement provided."
        # Get latest vacancy for this institute that is active
        latest_vacancy_qs = institute.vacancies.filter(is_active=True)
        if request.user.is_authenticated and not request.user.is_superuser and hasattr(request.user, 'adminrole'):
            latest_vacancy_qs = latest_vacancy_qs.filter(uploaded_by=request.user)
        latest_vacancy = latest_vacancy_qs.order_by('-created_at').first()
        
        prt_list = []
        tgt_list = []
        pgt_list = []
        other_list = []
        categories = []
        subjects = []
        selected_type_display = ""

        if latest_vacancy:
            # Group posts
            # Get IDs of posts the user has already applied to or marked not interested
            excluded_post_ids = []
            if request.user.is_authenticated:
                excluded_post_ids = UserApplication.objects.filter(
                    user=request.user, 
                    status__in=['applied', 'not_interested']
                ).values_list('vacancy_post_id', flat=True)

            # HRs always see all subjects for testing, skip exclusion
            is_hr_tester = request.user.is_authenticated and not request.user.is_superuser and hasattr(request.user, 'adminrole')

            posts = latest_vacancy.posts.all()
            for p in posts:
                # Skip if user applied or is not interested (unless HR testing)
                if not is_hr_tester and p.id in excluded_post_ids:
                    continue

                item = {'name': p.subject}
                if p.category == 'prt': prt_list.append(item)
                elif p.category == 'tgt': tgt_list.append(item)
                elif p.category == 'pgt': pgt_list.append(item)
                else: other_list.append(item)

            # Dynamic unique categories present in the active posts
            active_posts = posts if is_hr_tester else posts.exclude(id__in=excluded_post_ids)
            seen_categories = {}
            for p in active_posts:
                cat_slug = p.category.strip().lower()
                if cat_slug not in seen_categories:
                    # Format display name beautifully
                    words = cat_slug.split()
                    formatted_words = []
                    for word in words:
                        if word in ['upsc', 'ntt', 'pgt', 'tgt', 'prt', 'ctet', 'b.ed', 'dsssb', 'cbse', 'icse', 'ib']:
                            formatted_words.append(word.upper())
                        else:
                            formatted_words.append(word.capitalize())
                    display_name = " ".join(formatted_words)
                    
                    seen_categories[cat_slug] = {
                        'slug': cat_slug,
                        'display_name': display_name,
                    }
            categories = list(seen_categories.values())
            
            # If a specific type is selected, filter subjects for that type
            if vacancy_type:
                # Format selected_type_display beautifully
                words = vacancy_type.strip().split()
                formatted_words = []
                for word in words:
                    if word.lower() in ['upsc', 'ntt', 'pgt', 'tgt', 'prt', 'ctet', 'b.ed', 'dsssb', 'cbse', 'icse', 'ib']:
                        formatted_words.append(word.upper())
                    else:
                        formatted_words.append(word.capitalize())
                selected_type_display = " ".join(formatted_words)

                # We need to re-filter specifically for the selected type's subjects list
                filtered_posts = active_posts.filter(category=vacancy_type.strip().lower())
                seen_subjects = set()
                for fp in filtered_posts:
                    sub_clean = fp.subject.strip()
                    # Format subject display beautifully
                    sub_words = sub_clean.split()
                    formatted_sub_words = []
                    for word in sub_words:
                        if word.lower() in ['upsc', 'ntt', 'pgt', 'tgt', 'prt', 'gk', 'gs', 'ssc', 'net', 'csir', 'gate', 'cat', 'clat', 'iit', 'jee', 'neet']:
                            formatted_sub_words.append(word.upper())
                        else:
                            formatted_sub_words.append(word.capitalize())
                    sub_display = " ".join(formatted_sub_words)
                    
                    if sub_display.lower() not in seen_subjects:
                        seen_subjects.add(sub_display.lower())
                        subjects.append({
                            'raw': sub_clean,
                            'display': sub_display
                        })
                
    return render(request, 'core/institute_detail.html', {
        'state_name': state_name,
        'district_name': district_name,
        'institute_name': institute_name,
        'current_category': category,
        'category_title': category_title,
        'belief': belief,
        'prt_list': prt_list,
        'tgt_list': tgt_list,
        'pgt_list': pgt_list,
        'other_list': other_list,
        'categories': categories,
        'selected_type': vacancy_type,
        'selected_type_display': selected_type_display,
        'subjects': subjects,
        'images': institute.images.all() if institute else []
    })

def vacancy_detail_view(request, state_name, district_name, institute_name, subject_name):
    category = request.GET.get('category', 'govt')
    vacancy_type = request.GET.get('type', 'other') # Default to other if not specified

    # Fetch specific post
    post_qs = VacancyPost.objects.filter(
        vacancy__institute__name=institute_name.strip(),
        vacancy__institute__state=state_name.strip(),
        vacancy__institute__district=district_name.strip(),
        category=vacancy_type.strip().lower(),
        subject=subject_name.strip().lower()
    )
    if request.user.is_authenticated and not request.user.is_superuser and hasattr(request.user, 'adminrole'):
        post_qs = post_qs.filter(vacancy__uploaded_by=request.user)
        
    post = post_qs.order_by('-vacancy__created_at').first()

    if post:
        # HR Testing Mode check
        is_test_mode = request.user.is_authenticated and post.vacancy.uploaded_by == request.user
        
        # Skip tracking if in test mode
        if request.user.is_authenticated and not is_test_mode:
            try:
                if hasattr(request.user, 'verification'):
                    request.user.verification.viewed_vacancies.add(post)
            except Exception:
                pass
                
        qualification = post.qualification
        compensation = post.compensation
        eligibility = post.eligibility
        age_limit = post.age_limit
        app_link = post.vacancy.application_link or ""
        post_id = post.id
        total_posts = post.total_posts
    else:
        # Fallback for deleted vacancy when user clicks from email
        return render(request, 'core/vacancy_closed.html')
        compensation = "NA"
        eligibility = "NA"
        age_limit = "NA"
        app_link = ""
        post_id = None
        total_posts = ""

    # Category display name
    category_titles = {
        'govt': 'Government',
        'semi': 'Semi-Government',
        'private': 'Private',
        'coaching': 'Coaching'
    }
    category_title = category_titles.get(category, 'Other')
    vacancy_type_label = vacancy_type.upper()
    
    # Determine if application link is an email
    app_link_str = str(app_link).strip()
    is_email = '@' in app_link_str and not app_link_str.lower().startswith('http')
    
    # Generate Mailto Link ONLY if it's an email
    if is_email:
        # Pass the post owner (HR) to ensure their template is used and docs are hidden
        mailto_link = generate_mailto_link(request, vacancy_type, subject_name, app_link_str, owner=post.vacancy.uploaded_by)
    else:
        mailto_link = ""
        # Ensure URLs have http/https prefix if it looks like a domain
        if app_link_str and not app_link_str.lower().startswith('http') and not is_email:
            app_link = "https://" + app_link_str

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
        'is_email': is_email,
        'post_id': post_id,
        'mailto_link': mailto_link,
        'is_test_mode': is_test_mode,
        'total_posts': total_posts
    })

def generate_mailto_link(request, category, subject, application_email=None, owner=None):
    """
    Helper to generate a mailto link with pre-filled subject and body.
    Includes links to user's uploaded documents if authenticated.
    """
    from .models import EmailTemplate, UserVerification
    import urllib.parse
    
    # 1. Find Template - Prioritize the owner's private template if provided
    template = None
    if owner:
        template = EmailTemplate.objects.filter(
            user=owner,
            category=category.strip().lower(), 
            subject=subject.strip().lower()
        ).first()
    
    # Fallback to general template if owner's not found or not provided
    if not template:
        template = EmailTemplate.objects.filter(
            user__isnull=True,
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
    # DO NOT append if the user is the owner (HR testing mode)
    if request.user.is_authenticated and request.user != owner:
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
            return redirect('admin_dashboard' if (user.is_staff or hasattr(user, 'adminrole')) else 'user_dashboard')
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
            
            return redirect('admin_dashboard' if (user.is_staff or hasattr(user, 'adminrole')) else 'user_dashboard')
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
    is_superadmin = request.user.is_superuser
    has_role = hasattr(request.user, 'adminrole')
    
    if not (is_superadmin or has_role):
        return redirect('user_dashboard')
        
    is_hr = not is_superadmin and has_role
    assigned_roles = request.user.adminrole.roles if has_role else []
    if is_superadmin:
        assigned_roles = ['all']

    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create()
    
    # --- Automated Cleaning: Expire vacancies older than 10 days ---
    cutoff_date = timezone.now() - timedelta(days=10)
    # Perform soft-delete (is_active=False) on old active vacancies
    Vacancy.objects.filter(is_active=True, created_at__lt=cutoff_date).update(is_active=False)
    # Optional: Log or print expired_count if debugging needed
    # -------------------------------------------------------------

    # Fetch Email Templates for display - Private to the HR
    from .models import EmailTemplate
    email_templates = EmailTemplate.objects.filter(user=request.user).order_by('category', 'subject')

    # Fetch Submitted Vacancies - Only active ones, annotated with applicant count
    submitted_vacancies_qs = Vacancy.objects.filter(is_active=True)
    if is_hr:
        submitted_vacancies_qs = submitted_vacancies_qs.filter(uploaded_by=request.user)
    
    submitted_vacancies = submitted_vacancies_qs.annotate(
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
            institute_name = request.POST.get('institute_name', '').strip()
            category = request.POST.get('institute_category', '').strip()
            state = request.POST.get('state', '').strip()
            district = request.POST.get('district', '').strip()
            belief = request.POST.get('belief', '').strip()
            app_link = request.POST.get('application_link', '').strip()

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
                application_link=app_link,
                uploaded_by=request.user
            )

            # Create Posts
            categories = request.POST.getlist('post_category[]')
            subjects = request.POST.getlist('post_subject[]')
            qualifications = request.POST.getlist('post_qualification[]')
            compensations = request.POST.getlist('post_compensation[]')
            eligibilities = request.POST.getlist('post_eligibility[]')
            age_limits = request.POST.getlist('post_age_limit[]')
            total_posts_list = request.POST.getlist('post_total_posts[]')

            for i in range(len(categories)):
                VacancyPost.objects.create(
                    vacancy=vacancy,
                    category=categories[i].strip(),
                    subject=subjects[i].strip(),
                    qualification=qualifications[i] if i < len(qualifications) else "NA",
                    compensation=compensations[i] if i < len(compensations) else "NA",
                    eligibility=eligibilities[i] if i < len(eligibilities) else "NA",
                    age_limit=age_limits[i] if i < len(age_limits) else "NA",
                    total_posts=total_posts_list[i] if i < len(total_posts_list) else ""
                )
            
            # In a real app we'd redirect with a success message
            return redirect('admin_dashboard')

        # Handle "Upload Syllabus" submission
        elif 'upload_syllabus' in request.POST:
            try:
                from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic, GuidanceTopicFile, User
                from django.utils.text import slugify
                
                target_audience = request.POST.get('target_audience')
                category_input = request.POST.get('guidance_category', '').strip()
                subject_name = request.POST.get('subject_name')
                
                # Find or Create Category
                if category_input:
                    category_slug = slugify(category_input)
                    if not category_slug:
                        category_slug = "other"
                    
                    # Ensure name display is neat (e.g. "PRT", "Librarian")
                    category_name = category_input
                    if category_slug in ['prt', 'tgt', 'pgt', 'other']:
                        category_name = category_input.upper()
                    
                    category, _ = GuidanceCategory.objects.get_or_create(
                        slug=category_slug,
                        defaults={'name': category_name}
                    )
                    
                    # Find or Create Subject (Case and whitespace insensitive)
                    subject_name_clean = subject_name.strip()
                    norm_target = "".join(subject_name_clean.split()).lower()
                    
                    existing_subjects = GuidanceSubject.objects.filter(category=category)
                    subject = None
                    for sub in existing_subjects:
                        if "".join(sub.name.split()).lower() == norm_target:
                            subject = sub
                            break
                    
                    if not subject:
                        subject = GuidanceSubject.objects.create(
                            category=category,
                            name=subject_name_clean
                        )
                    
                    # Handle Topics
                    topic_limit = int(request.POST.get('topic_count', 0))
                    
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

                        import re
                        import os

                        def sanitize_filename(filename):
                            # Replace spaces and special characters with underscores
                            name, ext = os.path.splitext(filename)
                            name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
                            return name + ext

                        # Handle Multiple Files
                        # PPTs
                        if request.FILES.getlist(f'topic_ppt_{i}[]'):
                            for f in request.FILES.getlist(f'topic_ppt_{i}[]'):
                                f.name = sanitize_filename(f.name)
                                GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='ppt')
                        
                        # PDFs
                        if request.FILES.getlist(f'topic_pdf_{i}[]'):
                            for f in request.FILES.getlist(f'topic_pdf_{i}[]'):
                                f.name = sanitize_filename(f.name)
                                GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='pdf')

                        # Images
                        if request.FILES.getlist(f'topic_image_{i}[]'):
                            for f in request.FILES.getlist(f'topic_image_{i}[]'):
                                f.name = sanitize_filename(f.name)
                                GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='image')

                        # ===== Save MCQ Section =====
                        mcq_mode = request.POST.get(f'topic_mcq_mode_{i}', 'none')
                        if mcq_mode in ['ai', 'manual']:
                            try:
                                timer_mins = int(request.POST.get(f'topic_mcq_timer_{i}', 10))
                            except ValueError:
                                timer_mins = 10

                            raw_json = ''
                            if mcq_mode == 'ai':
                                raw_json = request.POST.get(f'topic_mcq_json_{i}', '').strip()
                            elif mcq_mode == 'manual':
                                raw_json = request.POST.get(f'topic_mcq_manual_json_{i}', '').strip()

                            if raw_json:
                                try:
                                    questions_data = json.loads(raw_json)
                                    if isinstance(questions_data, list) and len(questions_data) > 0:
                                        from .models import MCQSet, MCQ, MCQOption
                                        mcq_set = MCQSet.objects.create(
                                            topic=topic,
                                            time_limit_minutes=timer_mins
                                        )
                                        for q_idx, q_item in enumerate(questions_data):
                                            # --- Flexible key resolution ---
                                            q_text = (
                                                q_item.get('question') or
                                                q_item.get('question_text') or
                                                q_item.get('text') or ''
                                            ).strip()
                                            if not q_text:
                                                continue
                                            options_list = (
                                                q_item.get('options') or
                                                q_item.get('choices') or
                                                q_item.get('answers') or []
                                            )
                                            correct_raw = (
                                                q_item.get('correct') if q_item.get('correct') is not None
                                                else q_item.get('correct_index', q_item.get('correct_option', q_item.get('answer', 0)))
                                            )
                                            correct_idx = 0
                                            if isinstance(correct_raw, int):
                                                correct_idx = correct_raw
                                            elif isinstance(correct_raw, str):
                                                val = correct_raw.strip()
                                                if len(val) == 1 and val.upper() in 'ABCDEFGHIJ':
                                                    correct_idx = ord(val.upper()) - 65
                                                else:
                                                    try:
                                                        correct_idx = int(val)
                                                    except ValueError:
                                                        # match text to option
                                                        for oi, ot in enumerate(options_list):
                                                            if str(ot).strip().lower() == val.lower():
                                                                correct_idx = oi
                                                                break

                                            mcq_question = MCQ.objects.create(
                                                mcq_set=mcq_set,
                                                question_text=q_text,
                                                order=q_idx + 1
                                            )
                                            for opt_idx, opt_text in enumerate(options_list[:10]):
                                                label = chr(65 + opt_idx)
                                                MCQOption.objects.create(
                                                    mcq=mcq_question,
                                                    label=label,
                                                    option_text=str(opt_text).strip(),
                                                    is_correct=(opt_idx == correct_idx)
                                                )
                                except Exception as json_err:
                                    import traceback
                                    print(f"Error parsing MCQ JSON for topic {i}:", json_err)
                                    print(traceback.format_exc())

                        # ===== Save Answer Writing Section =====
                        answer_questions_list = request.POST.getlist(f'topic_answer_questions_{i}[]')
                        if not answer_questions_list:
                            raw_text = request.POST.get(f'topic_answer_questions_{i}', '').strip()
                            if raw_text:
                                answer_questions_list = [q.strip() for q in raw_text.split('\n') if q.strip()]
                                
                        if answer_questions_list:
                            from .models import AnswerWritingQuestion
                            for q_text in answer_questions_list:
                                q_text_clean = q_text.strip()
                                if q_text_clean:
                                    AnswerWritingQuestion.objects.create(topic=topic, question_text=q_text_clean)
                
                return redirect('admin_dashboard')
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print("Syllabus Upload Error:", error_trace)
                return JsonResponse({
                    'success': False, 
                    'error': str(e),
                    'traceback': error_trace
                }, status=500)
            
        elif 'save_email_template' in request.POST:
            from .models import EmailTemplate
            cat = request.POST.get('template_category', '').strip().lower()
            sub = request.POST.get('template_subject', '').strip().lower()
            
            template, _ = EmailTemplate.objects.get_or_create(
                user=request.user,
                category=cat,
                subject=sub
            )
            template.email_subject = request.POST.get('email_subject')
            template.email_body = request.POST.get('email_body')
            template.save()
            messages.success(request, f"Template for {cat.upper()} - {sub} saved!")
            return redirect('admin_dashboard')
            
        # Handle "Delete Email Template"
        elif 'delete_email_template' in request.POST:
            from .models import EmailTemplate
            t_id = request.POST.get('template_id')
            EmailTemplate.objects.filter(id=t_id).delete()
            return redirect('admin_dashboard')

        # Handle "Save Admin Roles"
        elif 'save_admin_roles' in request.POST:
            if is_superadmin:
                try:
                    hr_email = request.POST.get('hr_email', '').strip()
                    roles_json = request.POST.get('assigned_roles_json', '[]')
                    try:
                        roles = json.loads(roles_json)
                    except ValueError:
                        roles = []
                    
                    if hr_email:
                        is_delete = request.POST.get('delete_admin_roles', '0') == '1'
                        from django.contrib.auth.models import User
                        
                        if is_delete:
                            try:
                                target_user = User.objects.get(email=hr_email)
                                from .models import AdminRole
                                AdminRole.objects.filter(user=target_user).delete()
                                messages.success(request, f"Roles removed for {hr_email}")
                            except User.DoesNotExist:
                                messages.error(request, f"User {hr_email} not found")
                        else:
                            # Create or get user by email safely
                            target_user = User.objects.filter(email=hr_email).first()
                            if not target_user:
                                username_base = hr_email.split('@')[0]
                                username = username_base
                                # Resolve potential username conflicts
                                counter = 1
                                while User.objects.filter(username=username).exists():
                                    username = f"{username_base}{counter}"
                                    counter += 1
                                    
                                target_user = User.objects.create(
                                    email=hr_email,
                                    username=username,
                                    is_staff=True
                                )
                            else:
                                # Ensure existing user has staff flag to access dashboard
                                if not target_user.is_staff:
                                    target_user.is_staff = True
                                    target_user.save()
                            
                            from .models import AdminRole
                            admin_role, _ = AdminRole.objects.get_or_create(user=target_user)
                            admin_role.roles = roles
                            admin_role.save()
                            messages.success(request, f"Roles updated for {hr_email}")
                    
                    return redirect('admin_dashboard')
                except Exception as e:
                    messages.error(request, f"Technical Error: {str(e)}")
                    return redirect('admin_dashboard')

    return render(request, 'core/admin_dashboard.html', {
        'settings': settings,
        'india_data': INDIA_DATA,
        'submitted_vacancies': submitted_vacancies,
        'email_templates': email_templates,
        'is_superadmin': is_superadmin,
        'is_hr': is_hr,
        'assigned_roles': assigned_roles,
    })

@login_required(login_url='login_view')
def edit_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    # Permission check: superuser OR the one who uploaded it
    if not request.user.is_superuser and vacancy.uploaded_by != request.user:
        return redirect('home')
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
        
        institute_name = request.POST.get('institute_name', '').strip()
        category = request.POST.get('institute_category', '').strip()
        state = request.POST.get('state', '').strip()
        district = request.POST.get('district', '').strip()
        belief = request.POST.get('belief', '').strip()
        app_link = request.POST.get('application_link', '').strip()

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
        # New VacancyPost objects default to alert_emails_sent=False,
        # and vacancy.created_at was just reset to now() above —
        # so the 10-minute countdown starts fresh automatically on re-submit.
        vacancy.posts.all().delete()
        
        categories = request.POST.getlist('post_category[]')
        subjects = request.POST.getlist('post_subject[]')
        qualifications = request.POST.getlist('post_qualification[]')
        compensations = request.POST.getlist('post_compensation[]')
        eligibilities = request.POST.getlist('post_eligibility[]')
        age_limits = request.POST.getlist('post_age_limit[]')
        total_posts_list = request.POST.getlist('post_total_posts[]')

        for i in range(len(categories)):
            VacancyPost.objects.create(
                vacancy=vacancy,
                category=categories[i].strip(),
                subject=subjects[i].strip(),
                qualification=qualifications[i] if i < len(qualifications) else "NA",
                compensation=compensations[i] if i < len(compensations) else "NA",
                eligibility=eligibilities[i] if i < len(eligibilities) else "NA",
                age_limit=age_limits[i] if i < len(age_limits) else "NA",
                total_posts=total_posts_list[i] if i < len(total_posts_list) else ""
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
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    # Permission check: superuser OR the one who uploaded it
    if not request.user.is_superuser and vacancy.uploaded_by != request.user:
        return redirect('home')
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
                try:
                    verification.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    verification.dob = None
            else:
                verification.dob = None
            
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
        'user_full_name': verification.full_name or target_user.email, # Override header name
        'india_data': INDIA_DATA,
        'location_preferences': verification.location_preferences or []
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
            # Update status
            app.status = 'applied'
            app.save()
            
            # Engagement Tracking for Daily Email Alerts
            try:
                if hasattr(request.user, 'verification'):
                    request.user.verification.alert_engagement_score += 1
                    request.user.verification.save()
            except Exception:
                pass
                
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

@login_required(login_url='login_view')
def get_admin_roles_api(request):
    """API endpoint to fetch existing roles for an HR user by email."""
    # Only superadmin can fetch other user's roles
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    email = request.GET.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'error': 'No email provided'}, status=400)
    
    user = User.objects.filter(email=email).first()
    if user and hasattr(user, 'adminrole'):
        return JsonResponse({'success': True, 'roles': user.adminrole.roles})
    
    return JsonResponse({'success': True, 'roles': []})

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
    from .models import GuidanceCategory, GuidanceTopic
    from django.db.models import Q
    from django.utils import timezone
    from datetime import timedelta

    if GuidanceCategory.objects.count() == 0:
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
    if not last_visit:
        last_visit = timezone.now() - timedelta(days=7)

    # helper to check if a category should blink (contains new content)
    def check_cat_blink(cat_slug):
        q = GuidanceTopic.objects.filter(
            subject__category__slug=cat_slug,
            created_at__gt=last_visit
        )
        if request.user.is_authenticated:
             return q.filter(Q(is_for_everyone=True) | Q(assigned_users=request.user)).exists()
        return q.filter(is_for_everyone=True).exists()

    # Retrieve all categories dynamically and attach the blink flag
    categories_list = list(GuidanceCategory.objects.all())
    for cat in categories_list:
        cat.should_blink = check_cat_blink(cat.slug)

    view_as_user = request.GET.get('view_as') if request.user.is_superuser else None
    
    return render(request, 'core/syllabus_landing.html', {
        'categories': categories_list,
        'view_as_user': view_as_user
    })

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
    from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic, MCQSet, MCQAttempt, UserTopicNotes
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
        return render(request, 'core/syllabus_topics.html', {
            'category': category, 
            'subject': subject,
            'topics': [], # Hide content
            'error_message': 'You do not have permission to view this topic.'
        })

    # MCQ Set
    mcq_set = getattr(topic, 'mcq_set', None)
    
    # User's latest attempt
    latest_attempt = None
    if mcq_set:
        latest_attempt = MCQAttempt.objects.filter(
            user=request.user, 
            mcq_set=mcq_set
        ).order_by('-attempted_at').first()

    # User's personal notes
    user_notes = UserTopicNotes.objects.filter(
        user=request.user, 
        topic=topic
    ).first()

    # Admin Analytics (All attempts distinct by user)
    all_attempts = []
    material_engagements = []
    if request.user.is_superuser:
        if mcq_set:
            raw_attempts = MCQAttempt.objects.filter(mcq_set=mcq_set).select_related('user').order_by('user', '-attempted_at')
            seen_users = set()
            for att in raw_attempts:
                if att.user.id not in seen_users:
                    all_attempts.append(att)
                    seen_users.add(att.user.id)
            all_attempts.sort(key=lambda x: x.attempted_at, reverse=True)
            
            for att in all_attempts:
                att.attempt_number = MCQAttempt.objects.filter(user=att.user, mcq_set=mcq_set).count()

        # Query all material engagements for this topic
        from .models import MaterialEngagement
        material_engagements = MaterialEngagement.objects.filter(topic=topic).select_related('user').order_by('-last_accessed')

    # Answer Writing Context
    from .models import AnswerWritingQuestion
    answer_writing_questions = list(AnswerWritingQuestion.objects.filter(topic=topic).order_by('created_at'))
    for q in answer_writing_questions:
        if request.user.is_superuser:
            q.all_submissions = q.submissions.all().select_related('user').order_by('-submitted_at')
        else:
            q.user_submission = q.submissions.filter(user=request.user).first()

    return render(request, 'core/syllabus_topic_detail.html', {
        'category': category,
        'subject': subject,
        'topic': topic,
        'mcq_set': mcq_set,
        'latest_attempt': latest_attempt,
        'user_notes': user_notes,
        'all_attempts': all_attempts,
        'material_engagements': material_engagements,
        'answer_writing_questions': answer_writing_questions,
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
    subject_id    = topic.subject.id
    category_slug = topic.subject.category.slug

    if request.method == 'POST':
        topic.delete()
        messages.success(request, 'Topic deleted successfully.')
        from django.urls import reverse
        url = reverse('syllabus_subject', kwargs={'category_slug': category_slug, 'subject_id': subject_id})
        view_as = request.GET.get('view_as')
        if view_as:
            url += f'?view_as={view_as}'
        return redirect(url)

    # GET: show a proper confirmation page
    return render(request, 'core/confirm_delete_topic.html', {
        'topic': topic,
        'category': topic.subject.category,
        'subject': topic.subject,
        'view_as_user': request.GET.get('view_as'),
    })


@login_required(login_url='login_view')
def delete_category(request, category_id):
    """Superadmin: permanently delete a GuidanceCategory and all its subjects/topics/MCQs."""
    if not request.user.is_superuser:
        return redirect('home')

    from .models import GuidanceCategory

    category = get_object_or_404(GuidanceCategory, id=category_id)

    if request.method == 'POST':
        cat_name = category.name
        category.delete()  # cascades to subjects → topics → files / MCQSets / attempts / notes
        messages.success(request, f"Category \'{cat_name}\' and all its content has been deleted.")
        return redirect('syllabus_landing')

    # GET: show confirmation page
    return render(request, 'core/confirm_delete_category.html', {
        'category': category,
    })


@login_required(login_url='login_view')
def add_mcq_to_topic(request, topic_id):
    """Superadmin: attach an MCQ set to an already-uploaded topic."""
    if not request.user.is_superuser:
        return redirect('home')

    from .models import GuidanceTopic, MCQSet, MCQ, MCQOption

    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    category_slug = topic.subject.category.slug
    subject_id    = topic.subject.id

    if request.method == 'POST':
        try:
            timer_mins = int(request.POST.get('mcq_timer', 10))
        except (ValueError, TypeError):
            timer_mins = 10

        raw_json = request.POST.get('mcq_json', '').strip()
        if not raw_json:
            messages.error(request, 'No MCQ data provided.')
            return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

        try:
            questions_data = json.loads(raw_json)
        except Exception:
            messages.error(request, 'Invalid JSON – please check the format.')
            return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

        if not isinstance(questions_data, list) or len(questions_data) == 0:
            messages.error(request, 'JSON must be a non-empty array of question objects.')
            return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

        # Delete existing MCQ set if present
        try:
            topic.mcq_set.delete()
        except Exception:
            pass

        mcq_set = MCQSet.objects.create(topic=topic, time_limit_minutes=timer_mins)

        saved_count = 0
        for q_idx, q_item in enumerate(questions_data):
            q_text = (
                q_item.get('question') or
                q_item.get('question_text') or
                q_item.get('text') or ''
            ).strip()
            if not q_text:
                continue

            options_list = (
                q_item.get('options') or
                q_item.get('choices') or
                q_item.get('answers') or []
            )

            correct_raw = (
                q_item.get('correct') if q_item.get('correct') is not None
                else q_item.get('correct_index', q_item.get('correct_option', q_item.get('answer', 0)))
            )
            correct_idx = 0
            if isinstance(correct_raw, int):
                correct_idx = correct_raw
            elif isinstance(correct_raw, str):
                val = correct_raw.strip()
                if len(val) == 1 and val.upper() in 'ABCDEFGHIJ':
                    correct_idx = ord(val.upper()) - 65
                else:
                    try:
                        correct_idx = int(val)
                    except ValueError:
                        for oi, ot in enumerate(options_list):
                            if str(ot).strip().lower() == val.lower():
                                correct_idx = oi
                                break

            mcq_q = MCQ.objects.create(mcq_set=mcq_set, question_text=q_text, order=q_idx + 1)
            for opt_idx, opt_text in enumerate(options_list[:10]):
                MCQOption.objects.create(
                    mcq=mcq_q,
                    label=chr(65 + opt_idx),
                    option_text=str(opt_text).strip(),
                    is_correct=(opt_idx == correct_idx)
                )
            saved_count += 1

        messages.success(request, f'{saved_count} MCQ question(s) saved for "{topic.title}".')
        return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

    return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)


@login_required(login_url='login_view')
def delete_mcq_from_topic(request, topic_id):
    """Superadmin: permanently delete the MCQSet from a GuidanceTopic."""
    if not request.user.is_superuser:
        return redirect('home')

    from .models import GuidanceTopic, MCQSet
    from django.contrib import messages

    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    category_slug = topic.subject.category.slug
    subject_id    = topic.subject.id

    try:
        mcq_set = topic.mcq_set
    except MCQSet.DoesNotExist:
        messages.error(request, 'No MCQ set found for this topic.')
        return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

    if request.method == 'POST':
        mcq_set.delete()
        messages.success(request, f'MCQ Set for "{topic.title}" has been deleted successfully.')
        return redirect('syllabus_topic_detail', category_slug=category_slug, subject_id=subject_id, topic_id=topic_id)

    # GET: render confirmation page
    return render(request, 'core/confirm_delete_mcq.html', {
        'topic': topic,
        'mcq_set': mcq_set,
        'category': topic.subject.category,
        'subject': topic.subject,
    })


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


@login_required(login_url='login_view')
def edit_subject_inline(request, subject_id):
    """Enables inline editing of a GuidanceSubject name, with automatic merging if the new name already exists."""
    if not request.user.is_superuser:
        return redirect('home')
        
    from .models import GuidanceSubject
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect
    
    subject = get_object_or_404(GuidanceSubject, id=subject_id)
    category = subject.category
    
    if request.method == 'POST':
        new_name = request.POST.get('subject_name', '').strip()
        
        if not new_name:
            messages.error(request, 'Subject name cannot be empty.')
            return redirect('syllabus_subject', category_slug=category.slug, subject_id=subject.id)
            
        norm_target = "".join(new_name.split()).lower()
        norm_current = "".join(subject.name.split()).lower()
        
        # If name is actually changed (casing, spaces, or spelling)
        if norm_target != norm_current:
            # Check for existing matching subject
            existing_subjects = GuidanceSubject.objects.filter(category=category).exclude(id=subject.id)
            target_sub = None
            for sub in existing_subjects:
                if "".join(sub.name.split()).lower() == norm_target:
                    target_sub = sub
                    break
            
            if target_sub:
                # Merge topics under the existing subject
                topics = subject.topics.all()
                topic_count = topics.count()
                for topic in topics:
                    topic.subject = target_sub
                    topic.save()
                
                # Delete the old empty subject
                subject.delete()
                
                messages.success(
                    request, 
                    f"Subject merged successfully! '{new_name}' already exists, so all {topic_count} topics were aligned under it."
                )
                return redirect('syllabus_subject', category_slug=category.slug, subject_id=target_sub.id)
        
        # Simple name change or casing update
        subject.name = new_name
        subject.save()
        messages.success(request, 'Subject name updated successfully.')
        
    return redirect('syllabus_subject', category_slug=category.slug, subject_id=subject.id)


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
                    UserReadVacancy.objects.get_or_create(user=request.user, vacancy=v)
            elif action == 'mark_unread':
                # Remove read records for all school vacancies
                UserReadVacancy.objects.filter(user=request.user, vacancy__in=school_vacancies).delete()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid method'})

@csrf_exempt
@login_required(login_url='login_view')
def save_location_preference(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            state = data.get('state')
            district = data.get('district')
            categories = data.get('categories', [])
            subjects = data.get('subjects', {}) # New: subjects object
            
            if not state or not district:
                return JsonResponse({'success': False, 'message': 'State and District are required'})
            
            from .models import UserVerification
            v, _ = UserVerification.objects.get_or_create(user=request.user)
            # Create a NEW list to ensure change detection
            prefs = list(v.location_preferences or [])
            
            # Update existing if state/district matches, otherwise append
            updated = False
            for p in prefs:
                if p.get('state') == state and p.get('district') == district:
                    p['categories'] = categories
                    p['subjects'] = subjects
                    updated = True
                    break
            
            if not updated:
                prefs.append({
                    'state': state,
                    'district': district,
                    'categories': categories,
                    'subjects': subjects
                })
                
            v.location_preferences = prefs
            v.save()
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return JsonResponse({'success': False, 'message': f"{str(e)}\n{error_details}"}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)

@csrf_exempt
@login_required(login_url='login_view')
def erase_location_preference(request):
    if request.method == 'POST':
        try:
            from .models import UserVerification
            v, _ = UserVerification.objects.get_or_create(user=request.user)
            v.location_preferences = []
            v.save()
            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            return JsonResponse({'success': False, 'message': f"{str(e)}\n{traceback.format_exc()}"}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)

@csrf_exempt
@login_required(login_url='login_view')
def mark_chat_read(request):
    """API to mark all admin messages as read for the current user"""
    if request.method == 'POST':
        from .models import ChatMessage
        ChatMessage.objects.filter(user=request.user, sender_is_admin=True, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


# ─────────────────────────────────────────
#  MCQ and User Notes Backend Views
# ─────────────────────────────────────────

@login_required(login_url='login_view')
def syllabus_topic_mcq_view(request, category_slug, subject_id, topic_id):
    """Renders the quiz interface for an MCQ set with a countdown timer."""
    from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic, MCQSet
    from django.shortcuts import get_object_or_404, render

    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    subject = get_object_or_404(GuidanceSubject, id=subject_id, category=category)
    topic = get_object_or_404(GuidanceTopic, id=topic_id, subject=subject)
    mcq_set = get_object_or_404(MCQSet, topic=topic)

    # Convert questions and options to list for template
    questions = mcq_set.questions.all().prefetch_related('options')

    return render(request, 'core/syllabus_topic_mcq.html', {
        'category': category,
        'subject': subject,
        'topic': topic,
        'mcq_set': mcq_set,
        'questions': questions,
    })


@csrf_exempt
@login_required(login_url='login_view')
def syllabus_topic_mcq_submit_view(request, topic_id):
    """Calculates and saves an MCQ attempt from JSON payload."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=405)

    from .models import GuidanceTopic, MCQSet, MCQAttempt, MCQAttemptAnswer, MCQOption, MCQ
    from django.shortcuts import get_object_or_404
    import json

    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    mcq_set = get_object_or_404(MCQSet, topic=topic)

    try:
        data = json.loads(request.body)
        user_answers = data.get('answers', {})  # Map of QuestionID string -> OptionID (int or null)
        time_taken = int(data.get('time_taken_seconds', 0))
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid payload format'}, status=400)

    questions = mcq_set.questions.all().prefetch_related('options')
    
    correct_cnt = 0
    wrong_cnt = 0
    skipped_cnt = 0
    total_cnt = len(questions)

    # Create the attempt object first
    attempt = MCQAttempt.objects.create(
        user=request.user,
        mcq_set=mcq_set,
        total_questions=total_cnt,
        time_taken_seconds=time_taken
    )

    # Process each question
    for question in questions:
        # Check user selection
        selected_opt_id = user_answers.get(str(question.id))
        selected_opt = None
        is_correct = False

        if selected_opt_id is not None:
            try:
                selected_opt = MCQOption.objects.get(id=int(selected_opt_id), mcq=question)
                if selected_opt.is_correct:
                    correct_cnt += 1
                    is_correct = True
                else:
                    wrong_cnt += 1
            except (MCQOption.DoesNotExist, ValueError):
                skipped_cnt += 1
        else:
            skipped_cnt += 1

        # Create attempt detail answer
        MCQAttemptAnswer.objects.create(
            attempt=attempt,
            mcq=question,
            selected_option=selected_opt,
            is_correct=is_correct
        )

    # Update attempt aggregate counts
    attempt.correct_count = correct_cnt
    attempt.wrong_count = wrong_cnt
    attempt.skipped_count = skipped_cnt
    attempt.save()

    return JsonResponse({
        'success': True,
        'correct': correct_cnt,
        'wrong': wrong_cnt,
        'skipped': skipped_cnt,
        'total': total_cnt,
        'attempt_id': attempt.id
    })


@csrf_exempt
@login_required(login_url='login_view')
def syllabus_topic_notes_save_view(request, topic_id):
    """Saves user personal notes for a GuidanceTopic. Enforces 5MB limit."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=405)

    from .models import GuidanceTopic, UserTopicNotes
    from django.shortcuts import get_object_or_404
    import json

    topic = get_object_or_404(GuidanceTopic, id=topic_id)
    
    try:
        data = json.loads(request.body)
        notes_text = data.get('notes', '')
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)

    # Limit to 5 MB
    MAX_BYTES = 5 * 1024 * 1024
    if len(notes_text.encode('utf-8')) > MAX_BYTES:
        return JsonResponse({'success': False, 'message': 'Notes size exceeds the 5 MB limit.'}, status=400)

    notes_obj, created = UserTopicNotes.objects.update_or_create(
        user=request.user,
        topic=topic,
        defaults={'notes_text': notes_text}
    )

    return JsonResponse({
        'success': True,
        'size_kb': notes_obj.notes_size_kb()
    })


@login_required(login_url='login_view')
def mcq_attempt_review_view(request, category_slug, subject_id, topic_id, attempt_id):
    """Renders the detailed question-by-question review of a saved MCQ attempt."""
    from .models import GuidanceCategory, GuidanceSubject, GuidanceTopic, MCQSet, MCQAttempt
    from django.shortcuts import get_object_or_404, render, redirect
    
    category = get_object_or_404(GuidanceCategory, slug=category_slug)
    subject = get_object_or_404(GuidanceSubject, id=subject_id, category=category)
    topic = get_object_or_404(GuidanceTopic, id=topic_id, subject=subject)
    attempt = get_object_or_404(MCQAttempt, id=attempt_id)
    
    # Ensure standard user can only review their own attempt (superusers can view all)
    if not request.user.is_superuser and attempt.user != request.user:
        return redirect('home')
        
    answers = attempt.answers.all().select_related('mcq').prefetch_related('mcq__options')
    
    return render(request, 'core/mcq_attempt_review.html', {
        'category': category,
        'subject': subject,
        'topic': topic,
        'attempt': attempt,
        'answers': answers,
        'initial_tab': request.GET.get('tab', 'wrong'),
    })


@csrf_exempt
@login_required(login_url='login_view')
def edit_category_inline(request, category_id):
    """Superadmin: inline renaming and potential merging of category name in guidance system."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        from .models import GuidanceCategory, GuidanceSubject
        from django.utils.text import slugify
        
        category = get_object_or_404(GuidanceCategory, id=category_id)
        new_name = request.POST.get('category_name', '').strip()
        
        if not new_name:
            return JsonResponse({'success': False, 'message': 'Category name cannot be empty.'}, status=400)
            
        new_slug = slugify(new_name)
        if not new_slug:
            new_slug = "other"
            
        # Check if another category with the same slug exists (case & whitespace merging)
        target_category = GuidanceCategory.objects.filter(slug=new_slug).exclude(id=category.id).first()
        if target_category:
            # MERGING WORKFLOW:
            # Move all subjects of current category into the target category
            subjects = GuidanceSubject.objects.filter(category=category)
            for sub in subjects:
                # Deduplicate subject name inside target category
                norm_name = "".join(sub.name.split()).lower()
                existing_sub = GuidanceSubject.objects.filter(category=target_category)
                matched_sub = None
                for es in existing_sub:
                    if "".join(es.name.split()).lower() == norm_name:
                        matched_sub = es
                        break
                
                if matched_sub:
                    # Move all topics from sub to matched_sub
                    for topic in sub.topics.all():
                        topic.subject = matched_sub
                        topic.save()
                    # Delete the empty sub
                    sub.delete()
                else:
                    sub.category = target_category
                    sub.save()
                    
            category.delete() # Safe cascading delete of any remaining empty elements
            return JsonResponse({'success': True, 'merged': True, 'redirect_url': '/guidance/'})
        else:
            category.name = new_name
            category.slug = new_slug
            category.save()
            return JsonResponse({'success': True, 'merged': False, 'new_slug': new_slug})
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@csrf_exempt
@login_required(login_url='login_view')
def edit_individual_mcq(request, mcq_id):
    """Superadmin: inline editing of an individual MCQ question text and option values."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        from .models import MCQ, MCQOption
        import json
        try:
            data = json.loads(request.body)
            question_text = data.get('question_text', '').strip()
            options = data.get('options', [])
            correct_label = data.get('correct_label', 'A').strip().upper()
            
            if not question_text:
                return JsonResponse({'success': False, 'message': 'Question text cannot be empty.'}, status=400)
                
            mcq = MCQ.objects.get(id=mcq_id)
            mcq.question_text = question_text
            mcq.save()
            
            # Rebuild options to prevent inconsistencies
            mcq.options.all().delete()
            for idx, opt_text in enumerate(options):
                label = chr(65 + idx)
                MCQOption.objects.create(
                    mcq=mcq,
                    label=label,
                    option_text=opt_text.strip(),
                    is_correct=(label == correct_label)
                )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@csrf_exempt
@login_required(login_url='login_view')
def delete_individual_mcq(request, mcq_id):
    """Superadmin: permanently delete a single MCQ question from an MCQ Set."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        from .models import MCQ
        try:
            mcq = MCQ.objects.get(id=mcq_id)
            mcq.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@csrf_exempt
@login_required(login_url='login_view')
def add_answer_writing_question(request, topic_id):
    """Superadmin: dynamically add a new Answer Writing question to a topic."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        from .models import GuidanceTopic, AnswerWritingQuestion
        import json
        try:
            data = json.loads(request.body)
            question_text = data.get('question_text', '').strip()
            if not question_text:
                return JsonResponse({'success': False, 'message': 'Question text cannot be empty.'}, status=400)
                
            topic = GuidanceTopic.objects.get(id=topic_id)
            q = AnswerWritingQuestion.objects.create(topic=topic, question_text=question_text)
            return JsonResponse({'success': True, 'question_id': q.id, 'question_text': q.question_text})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@csrf_exempt
@login_required(login_url='login_view')
def edit_answer_writing_question(request, question_id):
    """Superadmin: inline edit the question text of an Answer Writing question."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        from .models import AnswerWritingQuestion
        import json
        try:
            data = json.loads(request.body)
            question_text = data.get('question_text', '').strip()
            if not question_text:
                return JsonResponse({'success': False, 'message': 'Question text cannot be empty.'}, status=400)
                
            q = AnswerWritingQuestion.objects.get(id=question_id)
            q.question_text = question_text
            q.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@csrf_exempt
@login_required(login_url='login_view')
def delete_answer_writing_question(request, question_id):
    """Superadmin: permanently delete an Answer Writing question and any student submissions."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        from .models import AnswerWritingQuestion
        try:
            q = AnswerWritingQuestion.objects.get(id=question_id)
            q.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@login_required(login_url='login_view')
def submit_answer_writing(request, question_id):
    """Candidate: submit answer file or image (limit <= 4MB, unique per question per candidate)."""
    from .models import AnswerWritingQuestion, AnswerWritingSubmission
    from django.shortcuts import get_object_or_404
    
    question = get_object_or_404(AnswerWritingQuestion, id=question_id)
    
    if request.method == 'POST':
        submitted_file = request.FILES.get('submitted_file')
        if not submitted_file:
            return JsonResponse({'success': False, 'message': 'No file uploaded.'}, status=400)
            
        # Limit to 4MB
        if submitted_file.size > 4 * 1024 * 1024:
            return JsonResponse({'success': False, 'message': 'File size must not exceed 4MB.'}, status=400)
            
        submission, created = AnswerWritingSubmission.objects.get_or_create(
            question=question,
            user=request.user,
            defaults={'submitted_file': submitted_file}
        )
        if not created:
            submission.submitted_file = submitted_file
            submission.save()
            
        return JsonResponse({'success': True, 'filename': submitted_file.name})
        
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


@login_required(login_url='login_view')
def save_remark(request, submission_id):
    """Superadmin: write checking feedback remarks and upload checked files, with Gmail notification."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
    from .models import AnswerWritingSubmission
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    from django.template.loader import render_to_string
    from django.conf import settings
    
    submission = get_object_or_404(AnswerWritingSubmission, id=submission_id)
    
    if request.method == 'POST':
        try:
            remark_text = request.POST.get('remark_text', '').strip()
            remark_file = request.FILES.get('remark_file')
            send_notification = request.POST.get('send_notification', 'true') == 'true'
            
            submission.remark_text = remark_text
            if remark_file:
                if remark_file.size > 4 * 1024 * 1024:
                    return JsonResponse({'success': False, 'message': 'Remark file size must not exceed 4MB.'}, status=400)
                submission.remark_file = remark_file
                
            submission.remarked_at = timezone.now()
            submission.save()
            
            email_sent = False
            if send_notification:
                # Email Dispatch Workflow
                student = submission.user
                question = submission.question
                topic = question.topic
                subject = topic.subject
                category = subject.category
                
                scheme = 'https' if (request.is_secure() or request.headers.get('x-forwarded-proto') == 'https') else 'http'
                domain = f"{scheme}://{request.get_host()}"
                feedback_url = f"{domain}/guidance/{category.slug}/subject/{subject.id}/topic/{topic.id}/?tab=answers"
                
                remark_file_url = ''
                if submission.remark_file:
                    url = submission.remark_file.url
                    remark_file_url = url if url.startswith('http') else f"{domain}{url}"
                
                context = {
                    'user_name': student.first_name or student.username,
                    'question_text': question.question_text,
                    'remark_text': remark_text,
                    'feedback_url': feedback_url,
                    'has_remark_file': bool(submission.remark_file),
                    'remark_file_url': remark_file_url
                }
                
                html_content = render_to_string('core/emails/answer_writing_remark.html', context)
                text_content = (
                    f"Hi {context['user_name']},\n\n"
                    f"Your submission for the question \"{question.question_text}\" in topic \"{topic.title}\" has been reviewed by the admin.\n\n"
                    f"Remark: {remark_text}\n\n"
                    f"Check your feedback directly here: {feedback_url}"
                )
                
                subject_line = f"New Feedback on your Answer Writing! 📝 ({topic.title})"
                
                email_sent = send_notification_email(
                    subject=subject_line,
                    html_content=html_content,
                    text_content=text_content,
                    recipient=student.email,
                    email_type='answer_writing'
                )
                
            return JsonResponse({'success': True, 'email_sent': email_sent, 'notified': send_notification})
        except Exception as e:
            import traceback
            return JsonResponse({'success': False, 'message': str(e), 'traceback': traceback.format_exc()})
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


def send_notification_email(subject, html_content, text_content, recipient, email_type='answer_writing'):
    """Helper: Priority-throttled SMTP email dispatcher with 500/day limit tracking (executed asynchronously)."""
    import threading
    
    def target_send():
        from django.utils import timezone
        from .models import SentEmailLog
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from django.db import connection
        
        try:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            sent_today_count = SentEmailLog.objects.filter(sent_at__gte=today_start).count()
            
            # Strictly respect 500 emails/day threshold
            if sent_today_count >= 499:
                print("Email dispatch aborted: 500/day limit reached.")
                return
                
            # Secondary notifications limit at 450 to leave safety buffer for core alerts
            if email_type == 'answer_writing' and sent_today_count >= 450:
                print("Email dispatch aborted: answer writing notifications threshold reached.")
                return
                
            from_email = getattr(settings, 'EMAIL_HOST_USER', 'tapteacher.in@gmail.com')
            msg = EmailMultiAlternatives(subject, text_content, f"TapTeacher <{from_email}>", [recipient])
            msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            SentEmailLog.objects.create(email_type=email_type, recipient=recipient)
            print(f"Email successfully dispatched to {recipient} in background thread.")
        except Exception as e:
            print(f"Error dispatching email notification in background: {e}")
            import traceback
            traceback.print_exc()
        finally:
            connection.close()

    # Start sending in a separate background thread so we do not block Gunicorn request worker thread
    thread = threading.Thread(target=target_send)
    thread.daemon = True
    thread.start()
    return True


@login_required(login_url='login_view')
def track_material_engagement(request):
    """API endpoint to track when a candidate opens a PDF or clicks on a description link."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            topic_id = data.get('topic_id')
            action = data.get('action') # 'pdf' or 'link'
            
            if not topic_id or action not in ['pdf', 'link']:
                return JsonResponse({'success': False, 'message': 'Invalid parameters'}, status=400)
                
            from .models import GuidanceTopic, MaterialEngagement
            topic = get_object_or_404(GuidanceTopic, id=topic_id)
            
            engagement, created = MaterialEngagement.objects.get_or_create(
                user=request.user,
                topic=topic
            )
            
            if action == 'pdf':
                engagement.pdf_open_count += 1
            elif action == 'link':
                engagement.link_click_count += 1
                
            engagement.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'POST required'}, status=405)


def check_smtp_status(request):
    """Diagnostic endpoint to inspect settings and perform a fast socket connection test."""
    from django.conf import settings
    from django.http import JsonResponse
    import socket
    
    user = getattr(settings, 'EMAIL_HOST_USER', 'Not Set')
    pwd = getattr(settings, 'EMAIL_HOST_PASSWORD', 'Not Set')
    pwd_len = len(pwd) if pwd else 0
    pwd_masked = f"{pwd[:2]}...{pwd[-2:]}" if pwd_len > 4 else "Too short/empty"
    
    host = 'smtp.gmail.com'
    
    results = {}
    for port in [587, 465]:
        # Test default
        try:
            s = socket.create_connection((host, port), timeout=2.0)
            s.close()
            results[f'port_{port}_default'] = "SUCCESS"
        except Exception as err:
            results[f'port_{port}_default'] = f"FAILED: {err}"
            
        # Test IPv4
        try:
            ipv4_address = socket.gethostbyname(host)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((ipv4_address, port))
            s.close()
            results[f'port_{port}_ipv4'] = f"SUCCESS (connected to {ipv4_address})"
        except Exception as err:
            results[f'port_{port}_ipv4'] = f"FAILED: {err}"
            
    return JsonResponse({
        'email_host_user': user,
        'email_host_password_length': pwd_len,
        'email_host_password_masked': pwd_masked,
        'test_results': results
    })
