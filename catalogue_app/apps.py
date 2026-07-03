# catalogue_app/apps.py
from django.apps import AppConfig

class CatalogueAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogue_app'
    
    def ready(self):
        import catalogue_app.signals  # Active les signaux