from .base import *
from decouple import config

# ==========================================================================
# SETTINGS DEV – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Configuración para DEV del proyecto ReFit.
# ==========================================================================
# --------------------------------------------------------------------------
# Configuración base de datos
# --------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config("DB_NAME"),
        'USER': config("DB_USER"),
        'PASSWORD': config("DB_PASSWORD"),
        'HOST': config("DB_HOST", default='localhost'),
        'PORT': config("DB_PORT", cast=int),
    }
}
