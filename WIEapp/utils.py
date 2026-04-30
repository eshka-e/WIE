from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string


def generate_verification_token():
    return get_random_string(64)


def send_verification_email(user, token):
    """Отправляет письмо с ссылкой подтверждения"""
    verification_url = f"http://127.0.0.1:8000/verify-email/{token}/"

    send_mail(
        subject='Подтверждение email на WHOisE',
        message=f'Привет, {user.profile.display_name or user.username}!\n\n'
                f'Перейди по ссылке, чтобы подтвердить email:\n{verification_url}\n\n'
                f'Если ты не регистрировался на WHOisE — просто проигнорируй это письмо.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )