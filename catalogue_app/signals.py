# catalogue_app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Produit, Catalogue

@receiver(post_save, sender=Produit)
@receiver(post_delete, sender=Produit)
@receiver(post_save, sender=Catalogue)
@receiver(post_delete, sender=Catalogue)
def sync_to_sql_server(sender, instance, **kwargs):
    """Synchronisation automatique à chaque modification"""
    try:
        from .sql_sync import SQLServerSync
        sql_sync = SQLServerSync()
        sql_sync.sync_all()
        print(f"✅ Synchro auto après modification de {sender.__name__}")
    except Exception as e:
        print(f"⚠️ Erreur synchro: {e}")