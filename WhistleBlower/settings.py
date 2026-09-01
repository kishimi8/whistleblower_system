import os
from dotenv import load_dotenv
from import_export.formats.base_formats import CSV, XLSX,JSON
from pathlib import Path

from django.urls import reverse_lazy
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,web-app-1,web-app-2,web-app-3,nginx').split(',') if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'https://whistle.finance.gov.ng,http://localhost,https://localhost,http://127.0.0.1,https://127.0.0.1').split(',') if origin.strip()]

# Reverse Proxy & SSL Configuration (Nginx Ingress/HA)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True


# Application definition

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'compressor',
    'import_export',
    'djmoney',
    'reports',
   # 'django_admin_kubi',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'WhistleBlower.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
            ],
        },
    },
]

WSGI_APPLICATION = 'WhistleBlower.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'whistle'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Caching & Sessions (Centralized Redis for HA Multi-Replica State)
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'whistleblower-local-cache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'


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
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
# import and export settings
IMPORT_EXPORT_USE_TRANSACTIONS = True


# multiple import options
IMPORT_FORMATS = [CSV, XLSX,JSON]

# single export options
EXPORT_FORMATS = [XLSX, CSV]

##DJANGO_ADMIN_KUBI = {
#    'ADMIN_HISTORY': True,  # enables the history action panel
#    'ADMIN_SEARCH': True,  # enables a full modal search
#}
## ADMIN_MENU = "reports.admin_menu.MyAdminMenu"

# HTTPS settings
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
#SECURE_SSL_REDIRECT = True

# HSTS settings browsers wont conect over an unsecure connection disable in dev mode
##SECURE_HSTS_SECONDS = 31536000 # 1 year
##SECURE_HSTS_PRELOAD = True
##SECURE_HSTS_INCLUDE_SUBDOMAINS = True

#email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.entuitivesupport.com.ng'  # Use your email provider's SMTP server
EMAIL_PORT = 465
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'kishimi@entuitivesupport.com.ng'
EMAIL_HOST_PASSWORD = 'ibrokish08Escube!'

# Two-factor authentication settings
LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = 'two_factor:profile'
TWO_FACTOR_FORCE_OTP_ADMIN = True

UNFOLD = {
    "SITE_TITLE": "Whistleblowing Admin",
    "SITE_HEADER": "Whistleblowing System",
    "SITE_URL": "/",
    # "SITE_ICON": lambda request: static("icon.svg"),  # both modes, optimise for 32px height
    "DASHBOARD_CALLBACK": "reports.dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Navigation",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": "Reports",
                        "icon": "description",
                        "link": reverse_lazy("admin:reports_report_changelist"),
                    },
                ],
            },
        ],
    },
}