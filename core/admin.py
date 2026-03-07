from django.contrib import admin
from .models import SiteSettings, Institute, InstituteImage, Vacancy, VacancyPost, UserApplication, GuidanceCategory, GuidanceSubject, GuidanceTopic

admin.site.register(SiteSettings)

class PostInline(admin.TabularInline):
    model = VacancyPost
    extra = 1

class VacancyInline(admin.StackedInline):
    model = Vacancy
    extra = 0

@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    inlines = [VacancyInline]

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    inlines = [PostInline]

admin.site.register(VacancyPost)
admin.site.register(UserApplication)

# Syllabus Models
@admin.register(GuidanceCategory)
class GuidanceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(GuidanceSubject)
class GuidanceSubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(GuidanceTopic)
class GuidanceTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_for_everyone', 'created_at')
    list_filter = ('subject', 'is_for_everyone')
