from django.apps import AppConfig

class ReFitAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'refit_app'

def ready(self):
    import refit_app.signals
    