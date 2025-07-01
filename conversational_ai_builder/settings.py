"""
Django settings for Conversational AI Builder project.

This configuration file manages all Django settings for the conversational AI application
including database configuration, API integrations, security settings, and deployment
configurations for both development and production environments.

Key Features Configured:
- Multi-environment support (development/production)
- PostgreSQL and SQLite database support
- GitHub Models GPT-4 API integration
- Google Cloud Text-to-Speech API integration
- Security settings for production deployment
- Static file handling with WhiteNoise
- Media file management for audio storage

For more information on Django settings:
https://docs.djangoproject.com/en/5.2/topics/settings/
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# ========================================
# ENVIRONMENT AND PATH CONFIGURATION
# ========================================

# Load environment variables from .env file for local development
# This allows secure configuration without hardcoding sensitive values
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'
# This is the root directory of the Django project
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================================
# SECURITY CONFIGURATION
# ========================================

# SECURITY WARNING: keep the secret key used in production secret!
# Uses environment variable with fallback for development
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Debug mode provides detailed error pages but should be disabled in production
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Allowed hosts for the application
# In production, this should be set to your domain names
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ========================================
# EXTERNAL API CONFIGURATION
# ========================================

# GitHub Models API token for GPT-4 access
# Required for AI conversation functionality
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Google Cloud Text-to-Speech API Configuration
# Using API Key authentication (simple and unlimited)
# Required for voice synthesis functionality
GOOGLE_CLOUD_API_KEY = os.getenv('GOOGLE_CLOUD_API_KEY')

# Legacy authentication methods (NO LONGER NEEDED with API key)
# These are kept commented for reference but not used in current implementation
# GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
# GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
# GOOGLE_CLOUD_CREDENTIALS = os.getenv('GOOGLE_CLOUD_CREDENTIALS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bots',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conversational_ai_builder.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'conversational_ai_builder.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Check if psycopg2 is available
PSYCOPG2_AVAILABLE = False
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    print("Info: psycopg2 not available. Using SQLite for local development.")

# Use PostgreSQL (Supabase) if DATABASE_URL is provided and psycopg2 is available
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and PSYCOPG2_AVAILABLE:
    try:
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL)
        }
        print("Using PostgreSQL database from DATABASE_URL")
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}. Falling back to SQLite.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
elif os.getenv('DB_NAME') and PSYCOPG2_AVAILABLE:
    # Individual database settings (alternative to DATABASE_URL)
    try:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.getenv('DB_NAME'),
                'USER': os.getenv('DB_USER'),
                'PASSWORD': os.getenv('DB_PASSWORD'),
                'HOST': os.getenv('DB_HOST'),
                'PORT': os.getenv('DB_PORT', '5432'),
                'OPTIONS': {
                    'sslmode': 'require',
                },
            }
        }
        print("Using PostgreSQL database from individual settings")
    except Exception as e:
        print(f"Error configuring PostgreSQL: {e}. Using SQLite for development.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # Default to SQLite for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("Using SQLite database for local development")


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads, generated audio files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
