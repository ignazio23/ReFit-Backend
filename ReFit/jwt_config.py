from datetime import timedelta
from decouple import config

# --------------------------------------------------------------------------
# Información sobre TOKENS 
# --------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('SECRET_KEY'),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
