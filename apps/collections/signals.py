from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Collection
from .services import create_default_collection_settings


@receiver(post_save, sender=Collection)
def ensure_collection_settings(sender, instance, created, **kwargs):
    if created:
        create_default_collection_settings(instance)
