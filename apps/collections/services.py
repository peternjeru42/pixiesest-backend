from django.db import transaction
from django.utils import timezone

from apps.core.utils import unique_slugify

from .models import Collection, CollectionDesignSettings, CollectionDownloadSettings, CollectionPrivacySettings


def create_default_collection_settings(collection):
    CollectionPrivacySettings.objects.get_or_create(collection=collection)
    CollectionDownloadSettings.objects.get_or_create(collection=collection)
    CollectionDesignSettings.objects.get_or_create(collection=collection)


@transaction.atomic
def duplicate_collection(collection, owner):
    duplicate = Collection.objects.create(
        owner=owner,
        folder=collection.folder,
        title=f"{collection.title} Copy",
        slug=unique_slugify(Collection(owner=owner), f"{collection.title} Copy", queryset=Collection.all_objects.filter(owner=owner)),
        description=collection.description,
        event_date=collection.event_date,
        status="draft",
        visibility="private",
        sort_order=collection.sort_order + 1,
    )
    create_default_collection_settings(duplicate)
    return duplicate


def publish_collection(collection):
    collection.status = "published"
    collection.published_at = timezone.now()
    collection.save(update_fields=["status", "published_at", "updated_at"])
    return collection
