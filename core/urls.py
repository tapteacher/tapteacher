from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('state/<str:state_name>/', views.state_view, name='state_view'),
    path('state/<str:state_name>/<str:district_name>/', views.district_view, name='district_view'),
    path('state/<str:state_name>/<str:district_name>/<str:institute_name>/', views.institute_view, name='institute_view'),
    path('state/<str:state_name>/<str:district_name>/<str:institute_name>/vacancy/<path:subject_name>/', views.vacancy_detail_view, name='vacancy_detail_view'),
    path('login/', views.login_view, name='login_view'),
    path('google-login/', views.google_login_callback, name='google_login_callback'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/user/<int:user_id>/', views.user_dashboard, name='user_dashboard_admin'),
    path('manage/vacancy/delete/<int:vacancy_id>/', views.delete_vacancy, name='delete_vacancy'),
    path('manage/vacancy/edit/<int:vacancy_id>/', views.edit_vacancy, name='edit_vacancy'),
    path('manage/vacancy/applicants/<int:vacancy_id>/', views.vacancy_applicants, name='vacancy_applicants'),
    path('apply/<int:post_id>/', views.apply_to_vacancy, name='apply_to_vacancy'),
    path('save/<int:post_id>/', views.save_for_later, name='save_for_later'),
    path('not-interested/<int:post_id>/', views.mark_not_interested, name='mark_not_interested'),
    path('api/get-vacancy-details/', views.get_vacancy_details, name='get_vacancy_details'),
    path('logout/', views.logout_view, name='logout_view'),
    path('api/search-users/', views.search_users, name='search_users'),
    path('guidance/', views.syllabus_landing, name='syllabus_landing'),
    path('guidance/<slug:category_slug>/', views.syllabus_category_view, name='syllabus_category'),
    path('guidance/<slug:category_slug>/subject/<int:subject_id>/', views.syllabus_subject_view, name='syllabus_subject'),
    path('guidance/<slug:category_slug>/subject/<int:subject_id>/topic/<int:topic_id>/', views.syllabus_topic_detail_view, name='syllabus_topic_detail'),
    path('edit_topic_inline/<int:topic_id>/', views.edit_topic_inline, name='edit_topic_inline'),
    path('edit_subject_inline/<int:subject_id>/', views.edit_subject_inline, name='edit_subject_inline'),
    
    # New Edit Page Routes
    path('syllabus/category/<slug:category_slug>/subject/<int:subject_id>/topic/<int:topic_id>/edit/', 
         views.syllabus_topic_edit_view, name='syllabus_topic_edit'),
    path('delete_topic/<int:topic_id>/', views.delete_topic, name='delete_topic'),
    path('delete-topic-file/<int:file_id>/', views.delete_topic_file, name='delete_topic_file'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('add-mcq-to-topic/<int:topic_id>/', views.add_mcq_to_topic, name='add_mcq_to_topic'),
    path('delete-mcq-from-topic/<int:topic_id>/', views.delete_mcq_from_topic, name='delete_mcq_from_topic'),
    path('api/toggle-read/<int:vacancy_id>/', views.toggle_vacancy_read, name='toggle_vacancy_read'),
    
    # Admin User Management
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    
    # Chat URLs (using /manage/ to avoid conflict with Django admin)
    path('manage/chats/', views.user_chat_list, name='user_chat_list'),
    path('manage/chat/<int:user_id>/', views.user_chat_detail, name='user_chat_detail'),
    path('manage/chat/<int:user_id>/send/', views.admin_send_message, name='admin_send_message'),
    path('user/send-message/', views.user_send_message, name='user_send_message'),
    path('api/mark-chat-read/', views.mark_chat_read, name='mark_chat_read'),
    path('api/save-location-preference/', views.save_location_preference, name='save_location_preference'),
    path('api/erase-location-preference/', views.erase_location_preference, name='erase_location_preference'),
    path('api/get-admin-roles/', views.get_admin_roles_api, name='get_admin_roles_api'),
    
    # MCQ and User Notes Routes
    path('guidance/<slug:category_slug>/subject/<int:subject_id>/topic/<int:topic_id>/mcq/', views.syllabus_topic_mcq_view, name='syllabus_topic_mcq'),
    path('guidance/topic/<int:topic_id>/mcq/submit/', views.syllabus_topic_mcq_submit_view, name='syllabus_topic_mcq_submit'),
    path('guidance/topic/<int:topic_id>/notes/save/', views.syllabus_topic_notes_save_view, name='syllabus_topic_notes_save'),
    path('guidance/<slug:category_slug>/subject/<int:subject_id>/topic/<int:topic_id>/mcq/attempt/<int:attempt_id>/review/', views.mcq_attempt_review_view, name='mcq_attempt_review'),

    # Category edit URL
    path('edit_category_inline/<int:category_id>/', views.edit_category_inline, name='edit_category_inline'),
    
    # Inline MCQ edits
    path('edit_individual_mcq/<int:mcq_id>/', views.edit_individual_mcq, name='edit_individual_mcq'),
    path('delete_individual_mcq/<int:mcq_id>/', views.delete_individual_mcq, name='delete_individual_mcq'),
    
    # Answer Writing Admin Routes
    path('add_answer_writing_question/<int:topic_id>/', views.add_answer_writing_question, name='add_answer_writing_question'),
    path('edit_answer_writing_question/<int:question_id>/', views.edit_answer_writing_question, name='edit_answer_writing_question'),
    path('delete_answer_writing_question/<int:question_id>/', views.delete_answer_writing_question, name='delete_answer_writing_question'),
    
    # Answer Writing Student & Remark Routes
    path('submit_answer_writing/<int:question_id>/', views.submit_answer_writing, name='submit_answer_writing'),
    path('save_remark/<int:submission_id>/', views.save_remark, name='save_remark'),
    
    # Material Engagement Tracking
    path('api/track-material-engagement/', views.track_material_engagement, name='track_material_engagement'),
    
    # SMTP Diagnostics
    path('check_smtp_status/', views.check_smtp_status, name='check_smtp_status'),
]
