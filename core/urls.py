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
    
    # New Edit Page Routes
    path('syllabus/category/<slug:category_slug>/subject/<int:subject_id>/topic/<int:topic_id>/edit/', 
         views.syllabus_topic_edit_view, name='syllabus_topic_edit'),
    path('delete_topic/<int:topic_id>/', views.delete_topic, name='delete_topic'),
    path('delete-topic-file/<int:file_id>/', views.delete_topic_file, name='delete_topic_file'),
    path('api/toggle-read/<int:vacancy_id>/', views.toggle_vacancy_read, name='toggle_vacancy_read'),
    
    # Admin User Management
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    
    # Chat URLs (using /manage/ to avoid conflict with Django admin)
    path('manage/chats/', views.user_chat_list, name='user_chat_list'),
    path('manage/chat/<int:user_id>/', views.user_chat_detail, name='user_chat_detail'),
    path('manage/chat/<int:user_id>/send/', views.admin_send_message, name='admin_send_message'),
    path('user/send-message/', views.user_send_message, name='user_send_message'),
    path('api/mark-chat-read/', views.mark_chat_read, name='mark_chat_read'),
]
