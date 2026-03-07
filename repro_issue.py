import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import User, GuidanceCategory, GuidanceSubject, GuidanceTopic, UserVerification

def create_test_data():
    # 1. Create Student
    student, created = User.objects.get_or_create(email='teststudent@example.com', defaults={'username': 'teststudent'})
    if created:
        student.set_password('password123')
        student.save()
        print(f"Created Student: ID={student.id}")
    else:
        print(f"Index Student: ID={student.id}")

    # 2. Ensure Category
    cat, _ = GuidanceCategory.objects.get_or_create(slug='other', defaults={'name': 'Other Vacancy'})
    
    # 3. Ensure Subject
    sub, _ = GuidanceSubject.objects.get_or_create(category=cat, name='Personal Subject')
    
    # 4. Create Topic assigned to Student
    topic = GuidanceTopic.objects.create(
        subject=sub,
        title='Personal Topic For Delete',
        description='This is assigned to the student.',
        is_for_everyone=False
    )
    topic.assigned_users.add(student)
    topic.save()
    
    print(f"Created Personal Topic: ID={topic.id}, URL=/guidance/other/subject/{sub.id}/topic/{topic.id}/?view_as={student.id}")

if __name__ == '__main__':
    create_test_data()
