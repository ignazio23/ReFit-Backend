import os
from pathlib import Path
from decouple import config
from ReFit.jwt_config import SIMPLE_JWT

# ==========================================================================
# SETTINGS BASE – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Configuración base del proyecto ReFit.
# ==========================================================================
# --------------------------------------------------------------------------
# Base Directory
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --------------------------------------------------------------------------
# Seguridad y claves secretas
# --------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS").split(",")

# --------------------------------------------------------------------------
# Aplicaciones instaladas
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',

    # Propias
    'refit_app',
]

# --------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --------------------------------------------------------------------------
# Rutas de URL y plantillas
# --------------------------------------------------------------------------
ROOT_URLCONF = 'ReFit.urls'

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

WSGI_APPLICATION = 'ReFit.wsgi.application'

# --------------------------------------------------------------------------
# Autenticación y usuarios
# --------------------------------------------------------------------------
AUTH_USER_MODEL = 'refit_app.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
# --------------------------------------------------------------------------
# Internacionalización y zona horaria
# --------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Montevideo'
USE_I18N = True
#USE_L10N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Archivos estáticos y media
# --------------------------------------------------------------------------
MEDIA_URL = '/media/'
#MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'static'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------------------------------------------------
# CORS – Permitir conexiones desde frontend local
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

# --------------------------------------------------------------------------
# Configuración REST Framework + JWT
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# --------------------------------------------------------------------------
# LOGGING – Para monitoreo y debugging
# -------------------------------------------------------------------------- 
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': "test.log",
            'when': 'midnight',
            'backupCount': 5,
            'formatter': 'verbose',
            'delay': True,  # se agrega para retrasar la apertura del archivo
        },
    },
    'loggers': {
        'django': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'apps': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
