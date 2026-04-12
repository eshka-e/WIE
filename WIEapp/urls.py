from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'WIEapp'

urlpatterns = [
    path('', views.home, name='home'),
    path('stream/', views.stream_view, name='stream'),

    path('register/', views.register_view, name='register'),
    path('register/details/', views.register_details_view, name='register_details'),
    path('verify-email/sent/', views.verify_email_sent_view, name='verify_email_sent'),
path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('login/', auth_views.LoginView.as_view(template_name='WIEapp/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('space/<str:space_name>/', views.space_view, name='space'),

    path('impulse/<int:impulse_id>/', views.impulse_detail_view, name='impulse_detail'),
    path('impulse/create/', views.create_impulse_view, name='create_impulse'),
    path('impulse/<int:impulse_id>/edit/', views.edit_impulse_view, name='edit_impulse'),
    path('impulse/<int:impulse_id>/delete/', views.delete_impulse_view, name='delete_impulse'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),

    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/count/', views.unread_notifications_count, name='unread_count'),

    path('landmarks/', views.landmarks_view, name='landmarks'),
    path('followers/', views.followers_view, name='followers'),

    path('api/resonate/', views.toggle_resonance, name='toggle_resonance'),
    path('api/reply/', views.add_reply_ajax, name='add_reply_ajax'),
    path('api/landmark/', views.toggle_landmark, name='toggle_landmark'),

    path('faq/', views.faq_view, name='faq'),
    path('ask/', views.ask_question_view, name='ask_question'),

    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
]
