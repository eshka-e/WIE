from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'WIEapp'

urlpatterns = [
    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='WIEapp/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Главная (ПОТОК)
    path('', views.home, name='home'),  # это главная страница
    path('stream/', views.stream_view, name='stream'),

    # Пространства
    path('space/<str:space_name>/', views.space_view, name='space'),

    # Импульсы
    path('impulse/<int:impulse_id>/', views.impulse_detail_view, name='impulse_detail'),
    path('impulse/create/', views.create_impulse_view, name='create_impulse'),
    path('impulse/<int:impulse_id>/edit/', views.edit_impulse_view, name='edit_impulse'),
    path('impulse/<int:impulse_id>/delete/', views.delete_impulse_view, name='delete_impulse'),

    # Профили
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),

    # Уведомления
    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/count/', views.unread_notifications_count, name='unread_count'),

    # Ориентиры
    path('landmarks/', views.landmarks_view, name='landmarks'),
    path('followers/', views.followers_view, name='followers'),

    # API
    path('api/resonate/', views.toggle_resonance, name='toggle_resonance'),
    path('api/reply/', views.add_reply_ajax, name='add_reply_ajax'),
    path('api/landmark/', views.toggle_landmark, name='toggle_landmark'),

    # FAQ
    path('faq/', views.faq_view, name='faq'),
    path('ask/', views.ask_question_view, name='ask_question'),
]
