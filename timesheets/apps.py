from django.apps import AppConfig


class TimesheetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timesheets'
    
    def ready(self):
        import timesheets.signals  # Import signals