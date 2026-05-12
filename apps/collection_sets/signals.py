from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CollectionSet, SetStats


@receiver(post_save, sender=CollectionSet)
def create_set_stats(sender, instance, created, **kwargs):
    if created:
        SetStats.objects.get_or_create(set=instance)
