from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_user_defaults(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.profiles.models import UserProfile, UserProfileStats
    from apps.quotas.models import StorageQuota

    UserProfile.objects.get_or_create(
        user=instance,
        defaults={"display_name": instance.business_name or instance.email, "business_name": instance.business_name},
    )
    UserProfileStats.objects.get_or_create(user=instance)
    StorageQuota.objects.get_or_create(user=instance)
