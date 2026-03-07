from django.db import models
from django.contrib.auth.models import User

class SiteSettings(models.Model):
    youtube_link = models.CharField(max_length=255, default='@tapteacher', help_text="YouTube Link or Username")
    telegram_link = models.CharField(max_length=255, default='https://t.me/tapteacher', help_text="Telegram Link or Username")

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Singleton logic: ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            return SiteSettings.objects.first().save(*args, **kwargs)
        return super(SiteSettings, self).save(*args, **kwargs)

    @property
    def formatted_youtube_url(self):
        url = self.youtube_link.strip()
        if url.lower().startswith(('http://', 'https://')):
            return url
        # If it's a handle like @username, or just username
        if not url.startswith('@'):
            url = f"@{url}"
        return f"https://www.youtube.com/{url}"

    @property
    def formatted_telegram_url(self):
        url = self.telegram_link.strip()
        if url.lower().startswith(('http://', 'https://')):
            return url
        # Remove @ if present for t.me link construction, though t.me works with it sometimes, 
        # standard is t.me/username
        clean_username = url.lstrip('@')
        return f"https://t.me/{clean_username}"
class Institute(models.Model):
    CATEGORY_CHOICES = [
        ('govt', 'Government School'),
        ('semi', 'Semi-Government School'),
        ('private', 'Private School'),
        ('coaching', 'Private Coaching & Tution'),
    ]
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    belief = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.district}, {self.state})"

class InstituteImage(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='institute_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.institute.name}"

class Vacancy(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='vacancies')
    application_link = models.CharField(max_length=500)  # Link or Email
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vacancy for {self.institute.name}"

class VacancyPost(models.Model):
    POST_CATEGORY_CHOICES = [
        ('prt', 'PRT'),
        ('tgt', 'TGT'),
        ('pgt', 'PGT'),
        ('other', 'Other'),
    ]
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='posts')
    category = models.CharField(max_length=20, choices=POST_CATEGORY_CHOICES)
    subject = models.CharField(max_length=100)
    qualification = models.TextField(blank=True, default="NA")
    compensation = models.TextField(blank=True, default="NA")
    eligibility = models.TextField(blank=True, default="NA")
    age_limit = models.TextField(blank=True, default="NA")
    
    def save(self, *args, **kwargs):
        if self.category:
            self.category = self.category.strip().lower()
        if self.subject:
            self.subject = self.subject.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.upper()} - {self.subject} at {self.vacancy.institute.name}"

class UserApplication(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('saved', 'Saved for Later'),
        ('not_interested', 'Not Interested'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    vacancy_post = models.ForeignKey(VacancyPost, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'vacancy_post', 'status']

    def __str__(self):
        return f"{self.user.username} - {self.vacancy_post.subject} at {self.vacancy_post.vacancy.institute.name}"

class UserReadVacancy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_vacancies')
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'vacancy')
        indexes = [
            models.Index(fields=['user', 'vacancy']),
        ]

    def __str__(self):
        return f"{self.user.username} read vacancy at {self.vacancy.institute.name}"

# Syllabus / Guidance Models
class GuidanceCategory(models.Model):
    # e.g., PRT, TGT, PGT, Other
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class GuidanceSubject(models.Model):
    # e.g., English, Mathematics (linked to a category like PRT)
    category = models.ForeignKey(GuidanceCategory, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

class GuidanceTopic(models.Model):
    # e.g. "Chapter 1" with content
    subject = models.ForeignKey(GuidanceSubject, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Uploads
    ppt_file = models.FileField(upload_to='guidance/ppts/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='guidance/pdfs/', blank=True, null=True)
    image = models.ImageField(upload_to='guidance/images/', blank=True, null=True)
    
    # Access Control
    is_for_everyone = models.BooleanField(default=True)
    assigned_users = models.ManyToManyField(User, blank=True, related_name='assigned_guidance')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject}"

class GuidanceTopicFile(models.Model):
    topic = models.ForeignKey(GuidanceTopic, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='guidance/files/')
    file_type = models.CharField(max_length=20, choices=[('ppt', 'PPT'), ('pdf', 'PDF'), ('image', 'Image')], default='other')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_type.upper()} for {self.topic.title}"

class UserVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    
    # Unique ID logic: derived from DOB (Day + Year)
    unique_number = models.CharField(max_length=50, blank=True)
    
    additional_email = models.EmailField(blank=True, null=True)
    
    # Highest Qualification
    highest_qual_desc = models.TextField(blank=True)
    highest_qual_file = models.FileField(upload_to='verification/qualifications/', blank=True, null=True)
    
    # Certificate in Education
    edu_cert_desc = models.TextField(blank=True)
    edu_cert_file = models.FileField(upload_to='verification/certificates/', blank=True, null=True)
    
    # Experience
    exp_desc = models.TextField(blank=True)
    exp_file = models.FileField(upload_to='verification/experience/', blank=True, null=True)
    
    # Salary
    expected_salary = models.CharField(max_length=100, blank=True)
    salary_statement_file = models.FileField(upload_to='verification/salary/', blank=True, null=True)
    
    # Resume
    resume = models.FileField(upload_to='verification/resumes/', blank=True, null=True)
    
    # Track when user last visited syllabus for notification blinking
    last_syllabus_visit = models.DateTimeField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Generate Unique Number if not present or if DOB changed
        if self.dob:
            # Format: Day + Year (e.g. 17/02/2000 -> 172000)
            # We want literal string concatenation of day and year
            day = self.dob.day
            year = self.dob.year
            generated_id = f"{day}{year}"
            self.unique_number = generated_id
            
        super(UserVerification, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.unique_number}"


class ChatMessage(models.Model):
    """Model for storing chat messages between users and admins"""
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('pdf', 'PDF'),
        ('ppt', 'PowerPoint'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    sender_is_admin = models.BooleanField(default=False, help_text="True if admin sent this message")
    message_text = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        sender = "Admin" if self.sender_is_admin else self.user.username
        return f"{sender} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def attachment_filename(self):
        """Get just the filename from the attachment path"""
        if self.attachment:
            return self.attachment.name.split('/')[-1]
        return None
    
    @staticmethod
    def get_unread_count_for_user(user):
        """Get count of unread messages for a specific user (messages from admin)"""
        return ChatMessage.objects.filter(user=user, sender_is_admin=True, is_read=False).count()
    
    @staticmethod
    def get_users_with_messages():
        """Get all users who have chat messages, with their last message time and unread count"""
        from django.db.models import Max, Count, Q
        
        users_with_chats = User.objects.filter(
            chat_messages__isnull=False
        ).annotate(
            last_message_time=Max('chat_messages__created_at'),
            total_messages=Count('chat_messages'),
            unread_from_user=Count('chat_messages', filter=Q(chat_messages__sender_is_admin=False, chat_messages__is_read=False))
        ).order_by('-last_message_time')
        
        return users_with_chats

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_verification(sender, instance, created, **kwargs):
    if created:
        UserVerification.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_verification(sender, instance, **kwargs):
    try:
        instance.verification.save()
    except UserVerification.DoesNotExist:
        UserVerification.objects.create(user=instance)

class EmailTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('prt', 'PRT'),
        ('tgt', 'TGT'),
        ('pgt', 'PGT'),
        ('other', 'Other'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=100, help_text="e.g. Physics, Mathematics")
    email_subject = models.CharField(max_length=255, help_text="Subject line for the email")
    email_body = models.TextField(help_text="Body content for the email")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['category', 'subject']

    def save(self, *args, **kwargs):
        if self.category:
            self.category = self.category.strip().lower()
        if self.subject:
            self.subject = self.subject.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.upper()} - {self.subject}"
