from django.apps import AppConfig

class WIEappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'WIEapp'

    def ready(self):
        import WIEapp.signals