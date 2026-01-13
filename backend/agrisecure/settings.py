"""
AgriSecure IoT System - Django Settings
"""

import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    # WebSocket support
    'daphne',
    'channels',
    # WebSocket support
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'push_notifications',
    
    # AgriSecure Apps
    'apps.core',
    'apps.nodes',
    'apps.sensors',
    'apps.security',
    'apps.notifications',
    'apps.api',
    'apps.frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'agrisecure.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'agrisecure.wsgi.application'

# Database - PostgreSQL with TimescaleDB
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://agrisecure:agrisecure@localhost:5432/agrisecure',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Cache - Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===========================================
# Django REST Framework
# ===========================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF Spectacular (OpenAPI)
SPECTACULAR_SETTINGS = {
    'TITLE': 'AgriSecure IoT API',
    'DESCRIPTION': 'API per il sistema di monitoraggio agricolo e sicurezza perimetrale',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ORIGINS', 
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ===========================================
# Celery Configuration
# ===========================================
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ===========================================
# MQTT Configuration
# ===========================================
MQTT_CONFIG = {
    'BROKER': os.environ.get('MQTT_BROKER', 'localhost'),
    'PORT': int(os.environ.get('MQTT_PORT', 1883)),
    'USER': os.environ.get('MQTT_USER', 'agrisecure'),
    'PASSWORD': os.environ.get('MQTT_PASSWORD', ''),
    'KEEPALIVE': 60,
    'QOS': 1,
    'TOPICS': {
        'ROOT': 'agrisecure',
        'SENSORS': 'agrisecure/+/sensors/#',
        'SECURITY': 'agrisecure/+/security/#',
        'STATUS': 'agrisecure/+/status/#',
        'COMMAND': 'agrisecure/{gateway_id}/command',
    }
}

# ===========================================
# Notifications Configuration
# ===========================================

# Push Notifications (Firebase)
PUSH_NOTIFICATIONS_SETTINGS = {
    'FCM_API_KEY': os.environ.get('FCM_API_KEY', ''),
    'APNS_CERTIFICATE': os.environ.get('APNS_CERTIFICATE', ''),
    'UPDATE_ON_DUPLICATE_REG_ID': True,
}

# SMS (Twilio)
TWILIO_CONFIG = {
    'ACCOUNT_SID': os.environ.get('TWILIO_ACCOUNT_SID', ''),
    'AUTH_TOKEN': os.environ.get('TWILIO_AUTH_TOKEN', ''),
    'FROM_NUMBER': os.environ.get('TWILIO_FROM_NUMBER', ''),
}

# Telegram
TELEGRAM_CONFIG = {
    'BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'CHAT_ID': os.environ.get('TELEGRAM_CHAT_ID', ''),
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'AgriSecure <noreply@agrisecure.local>')

# ===========================================
# AgriSecure Custom Settings
# ===========================================
AGRISECURE = {
    # Soglie allarmi
    'ALARM_THRESHOLDS': {
        'TEMPERATURE_MIN': -5,      # °C - rischio gelo
        'TEMPERATURE_MAX': 45,      # °C - calore eccessivo
        'HUMIDITY_MIN': 20,         # % - aria troppo secca
        'HUMIDITY_MAX': 95,         # % - aria troppo umida
        'SOIL_MOISTURE_MIN': 15,    # % - suolo troppo secco
        'SOIL_MOISTURE_MAX': 85,    # % - suolo troppo bagnato
        'BATTERY_LOW': 20,          # % - batteria bassa
        'BATTERY_CRITICAL': 10,     # % - batteria critica
    },
    
    # Timeout nodi
    'NODE_TIMEOUT_WARNING': 3600,    # 1 ora - warning
    'NODE_TIMEOUT_CRITICAL': 7200,   # 2 ore - offline
    
    # Retention dati
    'DATA_RETENTION_DAYS': {
        'SENSOR_DATA': 365,          # 1 anno
        'SECURITY_EVENTS': 730,      # 2 anni
        'SYSTEM_LOGS': 90,           # 3 mesi
    },
    
    # Rate limiting notifiche
    'NOTIFICATION_COOLDOWN': {
        'CRITICAL': 60,              # 1 minuto tra notifiche critiche
        'WARNING': 300,              # 5 minuti tra warning
        'INFO': 3600,                # 1 ora tra info
    },
}

# ===========================================
# Login settings
# ===========================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ===========================================
# Logging
# ===========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'agrisecure.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'agrisecure': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'mqtt': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
(BASE_DIR / 'logs').mkdir(exist_ok=True)

# ============================================================
# Channels Configuration
# ============================================================

ASGI_APPLICATION = 'agrisecure.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# WebSocket settings
WEBSOCKET_ACCEPT_ALL = False
WEBSOCKET_HEARTBEAT_INTERVAL = 30

# ============================================================
# Channels Configuration
# ============================================================

ASGI_APPLICATION = 'agrisecure.asgi.application'

# WebSocket settings
WEBSOCKET_ACCEPT_ALL = False
WEBSOCKET_HEARTBEAT_INTERVAL = 30
