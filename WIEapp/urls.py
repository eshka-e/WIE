from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'WIEapp'

urlpatterns = [
    path('', views.home, name='home'),
    path('stream/', views.stream_view, name='stream'),

    path('register/', views.register_view, name='register'),
    path('verify-email/sent/', views.verify_email_sent_view, name='verify_email_sent'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('login/', auth_views.LoginView.as_view(template_name='WIEapp/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('spaces/', views.spaces_list_view, name='spaces_list'),
    path('space/<str:space_name>/', views.space_detail_view, name='space_detail'),

    path('impulse/<int:impulse_id>/', views.impulse_detail_view, name='impulse_detail'),
    path('impulse/create/', views.create_impulse_view, name='create_impulse'),
    path('impulse/<int:impulse_id>/edit/', views.edit_impulse_view, name='edit_impulse'),
    path('impulse/<int:impulse_id>/delete/', views.delete_impulse_view, name='delete_impulse'),

    # Профили
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),

    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/count/', views.unread_notifications_count, name='unread_count'),
    path('api/notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),

    path('landmarks/', views.landmarks_view, name='landmarks'),
    path('followers/', views.followers_view, name='followers'),

    path('api/resonate/', views.toggle_resonance, name='toggle_resonance'),
    path('api/reply/', views.add_reply_ajax, name='add_reply_ajax'),
    path('api/landmark/', views.toggle_landmark, name='toggle_landmark'),

    path('faq/', views.faq_view, name='faq'),
    path('ask/', views.ask_question_view, name='ask_question'),

    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('api/resonate/', views.toggle_resonance, name='toggle_resonance'),
    path('api/reply/', views.add_reply_ajax, name='add_reply_ajax'),
    path('api/landmark/', views.toggle_landmark, name='toggle_landmark'),
    path('api/notifications/count/', views.unread_notifications_count, name='unread_count'),
    path('api/follow/', views.toggle_follow, name='toggle_follow'),
    path('api/mute/', views.toggle_mute, name='toggle_mute'),
    path('api/report-user/', views.report_user, name='report_user'),
]
