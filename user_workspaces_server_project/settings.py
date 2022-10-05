"""
Django settings for user_workspaces_server_project project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import json
import os
from pathlib import Path
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG = json.load(open(
    os.path.join(BASE_DIR, 'example_config.json' if os.environ.get('GITHUB_WORKFLOW') else 'config.json')
))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/
django_settings = CONFIG['django_settings']
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = django_settings['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = django_settings['DEBUG']

ALLOWED_HOSTS = django_settings['ALLOWED_HOSTS']


# Application definition

INSTALLED_APPS = [
    'user_workspaces_server',
    'rest_framework',
    'rest_framework.authtoken',
    'django_q',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'corsheaders'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'user_workspaces_server_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'user_workspaces_server_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = django_settings['DATABASES']


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user_workspaces_server.auth.UserWorkspacesTokenAuthentication'
    ],
    'URL_FORMAT_OVERRIDE': None,
    'EXCEPTION_HANDLER': 'user_workspaces_server.exceptions.workspaces_exception_handler'
}

Q_CLUSTER = django_settings['Q_CLUSTER']

ASGI_APPLICATION = "user_workspaces_server_project.asgi.application"

CHANNEL_LAYERS = django_settings['CHANNEL_LAYERS']

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    "UWS-Authorization",
]

CSRF_TRUSTED_ORIGINS = django_settings['CSRF_TRUSTED_ORIGINS']

LOGGING = {
    'version': 1,
    'formatters': {
        'django-q': {
            'format': '{asctime} [Q] {levelname} {message}',
            'style': '{'
        },
        'user_workspaces_server': {
            'format': '{asctime} [UWS] {levelname} {message}',
            'style': '{'
        }
    },
    'handlers': {
        # Discard logging (for when a handler is mandatory).
        'discard': {
            'class': 'logging.NullHandler',
        },
        'django-q-console': {
            'class': 'logging.StreamHandler',
            'formatter': 'django-q',
        },
        'user_workspaces_server_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'user_workspaces_server'
        },
        'mail': {
            'class': 'user_workspaces_server.logging.AsyncEmailHandler',
            'formatter': 'user_workspaces_server',
            'level': 'ERROR',
            'subject': '',
            'from_email': '',
            'email_list': []
        }
    },
    'loggers': {
        'django-q': {
            'level': 'INFO',
            'propagate': True,
            'handlers': ['django-q-console'],
        },
        'user_workspaces_server': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': ['user_workspaces_server_console', 'mail']
        }
    }
}

EMAIL_HOST = django_settings['EMAIL_HOST']
EMAIL_HOST_USER = django_settings['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = django_settings['EMAIL_HOST_PASSWORD']
EMAIL_PORT = django_settings['EMAIL_PORT']
EMAIL_USE_TLS = django_settings['EMAIL_USE_TLS']
EMAIL_BACKEND = django_settings['EMAIL_BACKEND']
