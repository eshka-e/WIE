"""
Django settings for WHOisE project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-&nkxdctj(m6qp-+ft3dmf5o*x3!!785us6=6^udj=nr-z=&xvd')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['wewhoise.ru', 'www.wewhoise.ru', '62.109.13.38', 'localhost','127.0.0.1']

CSRF_TRUSTED_ORIGINS = ['https://wewhoise.ru', 'https://www.wewhoise.ru', 'http://62.109.13.38']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'WIEapp.apps.WIEappConfig',
    'micawber.contrib.mcdjango',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'WHOisE.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'WIEapp/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'WHOisE.wsgi.application'

# Database
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False') == 'True'

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'whoise_db'),
            'USER': os.getenv('DB_USER', 'whoise_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'WIEapp.backends.EmailOrUsernameBackend',
]

# Internationalization
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Login/Logout
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'WIEapp:stream'
LOGOUT_REDIRECT_URL = 'WIEapp:home'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'whoise.proj@yandex.ru'
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD', 'btzzcbhvedtnmhag')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# CSRF failure view
CSRF_FAILURE_VIEW = 'WIEapp.views.csrf_failure'

# Micawber oEmbed
import micawber
from micawber.providers import Provider

oembed_providers = micawber.bootstrap_basic()
oembed_providers.register('https://www.youtube.com/watch?v=*', Provider('https://www.youtube.com/oembed'))
oembed_providers.register('https://youtu.be/*', Provider('https://www.youtube.com/oembed'))
oembed_providers.register('https://vimeo.com/*', Provider('https://vimeo.com/api/oembed.json'))

OEMBED_PROVIDERS = oembed_providers