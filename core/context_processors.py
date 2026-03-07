def user_verification_context(request):
    """
    Context processor to make user verification data available in all templates
    """
    context = {
        'user_first_name': None,
        'user_full_name': None
    }
    if request.user.is_authenticated:
        try:
            # Safely try to access verification
            if hasattr(request.user, 'verification'):
                verification = request.user.verification
                if verification.full_name:
                    context['user_full_name'] = verification.full_name
                    context['user_first_name'] = verification.full_name.split()[0]
        except:
            pass
    return context

def site_settings(request):
    """
    Context processor to make site settings available in all templates
    """
    from .models import SiteSettings
    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create()
    return {'site_settings': settings}

def notification_flags(request):
    """
    Check for new content to set blink flags
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Vacancy, GuidanceTopic
    from django.db.models import Q
    
    flags = {
        'blink_govt': False,
        'blink_semi': False,
        'blink_private': False,
        'blink_coaching': False,
        'blink_syllabus': False,
    }
    
    # Vacancies: Blink if any active vacancy exists (since we auto-expire old ones)
    # Actually, we should double check the timestamps just in case expiration hasn't run yet for some reason,
    # but strictly speaking if is_active=True it's < 10 days old as per our new logic.
    # We will trust is_active=True for performance, but adding created_at check adds robustness.
    ten_days_ago = timezone.now() - timedelta(days=10)
    
    # Base query for ACTIVE vacancies (not soft deleted) and NEW (within 10 days)
    # Start with Institutes that have qualifying vacancies.
    # Note: A vacancy is basically an Institute (Vacancy model is actually Institute profile + vacancy details merged? 
    # Let's check model. Vacancy model IS the Institute essentially in this codebase structure based on previous views).
    # Wait, Vacancy model: "class Vacancy(models.Model): ... institute = models.ForeignKey(Institute...)"
    # Actually looking at views.py, `Vacancy.objects.filter` is used.
    
    base_qs = Vacancy.objects.filter(is_active=True, created_at__gte=ten_days_ago)
    
    # If user is logged in, exclude read vacancies
    if request.user.is_authenticated:
        # We can't easily join on UserReadVacancy from Vacancy direct without related_name or subquery.
        # But UserReadVacancy has 'vacancy' FK.
        # Let's get IDs of read vacancies.
        from .models import UserReadVacancy
        read_ids = UserReadVacancy.objects.filter(user=request.user).values_list('vacancy_id', flat=True)
        base_qs = base_qs.exclude(id__in=read_ids)

    def check_cat(cat_slug):
        # We need to find Vacancies that MATCH this category.
        # Vacancy has 'category' field? No. 
        # Vacancy has 'institute'. Institute has 'category'?
        # Let's check models.py quickly to be sure.
        # Assuming Vacancy has 'category' or similar based on existing context.
        # Actually in `home` view: `institutes = Vacancy.objects... if category: filter(category__iexact=category)`
        # So Vacancy has `category` field.
        return base_qs.filter(institute__category__iexact=cat_slug).exists()

    flags['blink_govt'] = check_cat('govt')
    flags['blink_semi'] = check_cat('semi')
    flags['blink_private'] = check_cat('private')
    flags['blink_coaching'] = check_cat('coaching')
    
    # Syllabus Logic
    
    # Determine the viewer's reference time for "active" or "new"
    # For Vacancies, it's fixed 10 days.
    # For Syllabus, it's relative to last visit.
    
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

    # Check for NEW topics since last visit
    # If never visited, any existing topic counts as new.
    # We can limit "new" to e.g. last 30 days to avoid eternal blinking for old content if user is new.
    
    # Base query
    topics_query = GuidanceTopic.objects.all()
    
    if last_visit:
        topics_query = topics_query.filter(created_at__gt=last_visit)
    else:
        # If no last visit, maybe just check if ANY exist? 
        # Or realistically, blink if anything was uploaded recently (e.g. 7 days).
        # Let's say if no visit record, we assume they haven't seen anything.
        # But we don't want to blink forever if the content is years old.
        cutoff_safe = timezone.now() - timedelta(days=7)
        topics_query = topics_query.filter(created_at__gt=cutoff_safe)

    if request.user.is_authenticated:
         # Personalization logic
         flags['blink_syllabus'] = topics_query.filter(
             Q(is_for_everyone=True) | Q(assigned_users=request.user)
         ).exists()
    else:
         # Guest logic - only everyone
         flags['blink_syllabus'] = topics_query.filter(is_for_everyone=True).exists()

    return flags
