from django.contrib import admin
from .models import (
    SiteSettings, Institute, InstituteImage, Vacancy, VacancyPost, UserApplication,
    GuidanceCategory, GuidanceSubject, GuidanceTopic, MCQSet, MCQ, MCQOption, AnswerWritingQuestion
)

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

# MCQ Inlines for Django Admin Panel
class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 4

@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'mcq_set', 'order')
    inlines = [MCQOptionInline]
    search_fields = ('question_text',)

class MCQInline(admin.TabularInline):
    model = MCQ
    extra = 1
    show_change_link = True

@admin.register(MCQSet)
class MCQSetAdmin(admin.ModelAdmin):
    list_display = ('topic', 'time_limit_minutes', 'question_count')
    inlines = [MCQInline]

class MCQSetInline(admin.StackedInline):
    model = MCQSet
    extra = 0

# Syllabus Models
@admin.register(GuidanceCategory)
class GuidanceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(GuidanceSubject)
class GuidanceSubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

class AnswerWritingQuestionInline(admin.TabularInline):
    model = AnswerWritingQuestion
    extra = 1

@admin.register(GuidanceTopic)
class GuidanceTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_for_everyone', 'created_at')
    list_filter = ('subject', 'is_for_everyone')
    inlines = [MCQSetInline, AnswerWritingQuestionInline]

admin.site.register(AnswerWritingQuestion)

