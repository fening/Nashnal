"""
Django settings for nst_timesheet project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path
import environ
import dj_database_url


env = environ.Env()
environ.Env.read_env()
ENVIRONMENT = env('ENVIRONMENT', default='development')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
if ENVIRONMENT == 'development':
    DEBUG = True
else:
    DEBUG = False
    
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'nashnal-production.up.railway.app',
    'www.google.com',
    'www.gstatic.com',
]

CSRF_TRUSTED_ORIGINS = ['https://nashnal-production.up.railway.app']

INTERNAL_IPS = ('127.0.0.1',
                'localhost:8080')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party apps
    'django_recaptcha',  # Only include once
    # Your apps
    'timesheets',
    'accounts',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'widget_tweaks',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.SessionTimeoutMiddleware',
]

# Remove CACHES setting entirely

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'timesheets.context_processors.notification_context',  # Add this line
            ],
        },
    },
]

# Add this section for notification settings
NOTIFICATION_SETTINGS = {
    'CLEAR_AFTER_DAYS': 30,  # Auto-clear notifications after 30 days
    'MAX_RECENT_NOTIFICATIONS': 5,  # Number of notifications to show in dropdown
}

# Remove these cache-related settings:
# - TEMPLATE_CACHE_TIMEOUT
# - CACHE_MIDDLEWARE_ALIAS
# - CACHE_MIDDLEWARE_SECONDS
# - CACHE_MIDDLEWARE_KEY_PREFIX

# Change session engine to db-only
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

ROOT_URLCONF = 'nst_timesheet.urls'

WSGI_APPLICATION = 'nst_timesheet.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# Determine if running locally or in production
# Environment variables

POSTGRES_LOCALLY = env.bool('POSTGRES_LOCALLY', default=False)

# Database settings
if ENVIRONMENT == 'production' or POSTGRES_LOCALLY:
    DATABASES = {
        'default': dj_database_url.parse(env('DATABASE_URL'))
    }
    print("Using production/POSTGRES_LOCALLY database:", DATABASES['default'])
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
        }
    }
    print("Using development database:", DATABASES['default'])

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')  # Common port for TLS
EMAIL_USE_TLS = env('EMAIL_USE_TLS')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')  # Use environment variable in production!
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# For development/testing, you can use Django's console email backend
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging configuration for email-related logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts.utils': {  # Logger for our email utilities
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# ...existing logging configuration...

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'accounts': {  # Add this logger for your accounts app
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_recaptcha': {  # Add this logger for recaptcha
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Google reCAPTCHA settings
RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_PUBLIC_KEY', default='')
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_PRIVATE_KEY', default='')
RECAPTCHA_REQUIRED_SCORE = 0.85

# Only enable reCAPTCHA if both keys are provided
RECAPTCHA_ENABLED = bool(RECAPTCHA_PUBLIC_KEY and RECAPTCHA_PRIVATE_KEY)

if DEBUG:
    print(f"reCAPTCHA Configuration:")
    print(f"Public Key: {RECAPTCHA_PUBLIC_KEY[:10]}..." if RECAPTCHA_PUBLIC_KEY else "No public key found")
    print(f"Private Key: {RECAPTCHA_PRIVATE_KEY[:10]}..." if RECAPTCHA_PRIVATE_KEY else "No private key found")
    print(f"reCAPTCHA Enabled: {RECAPTCHA_ENABLED}")
    
    # For development only
    if not RECAPTCHA_ENABLED:
        SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
        # Use test keys if no keys are provided
        RECAPTCHA_PUBLIC_KEY=''
        RECAPTCHA_PRIVATE_KEY=''
        print("Using reCAPTCHA test keys")

# For development only
if DEBUG:
    SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
    # Optional: Set proxy for development
    RECAPTCHA_PROXY = {
    }
else:
    RECAPTCHA_PROXY = None
    
    
# Add this to control whether reCAPTCHA is enabled
RECAPTCHA_ENABLED = not DEBUG

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/



STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT =os.path.join(BASE_DIR, 'staticfiles')

STATIC_URL = '/static/'

MEDIA_URL = '/media/'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": os.path.join(BASE_DIR, 'media'),
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Media files configuration
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Create media directory if it doesn't exist
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

LOGIN_REDIRECT_URL = '/dashboard/'  # or any view you want to redirect to after login
LOGOUT_REDIRECT_URL = 'login'

AUTH_USER_MODEL = 'accounts.CustomUser'

# Allow all origins for development (adjust this for production)
CORS_ALLOW_ALL_ORIGINS = True

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 hours in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = not DEBUG  # Use secure cookies in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # Protects against CSRF

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]