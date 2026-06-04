from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string


def generate_verification_token():
    return get_random_string(64)


def send_verification_email(user, token):
    """Отправляет письмо с ссылкой подтверждения"""
    # Используем домен сервера, а не localhost
    verification_url = f"http://62.109.13.38/verify-email/{token}/"

    # Безопасно получаем имя пользователя
    username = user.username
    if hasattr(user, 'profile') and user.profile and user.profile.display_name:
        username = user.profile.display_name

    send_mail(
        subject='Подтверждение email на WHOisE',
        message=f'Привет, {username}!\n\n'
                f'Перейди по ссылке, чтобы подтвердить email:\n{verification_url}\n\n'
                f'Если ты не регистрировался на WHOisE — просто проигнорируй это письмо.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )