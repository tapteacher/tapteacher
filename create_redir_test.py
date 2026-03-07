import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import User, GuidanceCategory, GuidanceSubject, GuidanceTopic

def create_debug_topic():
    # Ensure Category & Subject
    cat, _ = GuidanceCategory.objects.get_or_create(slug='other', defaults={'name': 'Other Vacancy'})
    sub, _ = GuidanceSubject.objects.get_or_create(category=cat, name='Debug Redirection Subject')
    
    # Create Topic for Everyone
    topic = GuidanceTopic.objects.create(
        subject=sub,
        title='Redirection Test Topic',
        description='Testing delete redirection.',
        is_for_everyone=True
    )
    
    print(f"Created Topic: ID={topic.id}")
    print(f"URL: /guidance/other/subject/{sub.id}/topic/{topic.id}/")

if __name__ == '__main__':
    create_debug_topic()
