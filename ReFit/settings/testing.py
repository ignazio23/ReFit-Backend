from .base import *
from sshtunnel import SSHTunnelForwarder
from decouple import config
import os

# ==========================================================================
# SETTINGS TEST – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Configuración para TEST del proyecto ReFit.
# ==========================================================================
# --------------------------------------------------------------------------
# Configuración de la base de datos con túnel opcional
# --------------------------------------------------------------------------
USE_SSH_TUNNEL = config("USE_SSH_TUNNEL", default=True, cast=bool)
ssh_password = config("SSH_PASSWORD", default=None)
server = None

if USE_SSH_TUNNEL:
    try:
        server = SSHTunnelForwarder(
            (config('SSH_HOST'), config('SSH_PORT', cast=int)),
            ssh_username=config('SSH_USER'),
            ssh_pkey=config('SSH_KEY') if not ssh_password else None,
            ssh_password=ssh_password,
            remote_bind_address=(config('DB_HOST'), config('DB_PORT', cast=int)),
            local_bind_address=('localhost', 5432)
        )
        server.start()
        os.environ['DB_HOST'] = 'localhost'
        print(f"Túnel SSH activo en localhost:{server.local_bind_port}")
    except Exception as e:
        print(f"Error estableciendo el túnel SSH: {e}")

# Configuración base de datos
DATABASES = {
    'default': {
        'ENGINE':'django.db.backends.postgresql',
        'NAME':config("DB_NAME"),
        'USER':config("DB_USER"),
        'PASSWORD':config("DB_PASSWORD"),
        'HOST':os.environ.get("DB_HOST", config("DB_HOST")),
        'PORT':config("DB_PORT", cast=int),
    }
}
