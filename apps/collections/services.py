from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.utils import unique_slugify
from apps.storage.services import delete_object

from .models import Collection, CollectionDesignSettings, CollectionDownloadSettings, CollectionPrivacySettings, generate_download_pin


def create_default_collection_settings(collection):
    download_pin = generate_download_pin()
    CollectionPrivacySettings.objects.get_or_create(
        collection=collection,
        defaults={
            "is_password_enabled": True,
            "password_hash": make_password(download_pin),
        },
    )
    CollectionDownloadSettings.objects.get_or_create(
        collection=collection,
        defaults={
            "download_pin_enabled": True,
            "download_pin": download_pin,
            "download_pin_hash": make_password(download_pin),
        },
    )
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


def _unique_media_storage_keys(media_assets):
    keys = set()
    for asset in media_assets:
        keys.update(
            key
            for key in (asset.original_file_key, asset.preview_file_key, asset.thumbnail_file_key)
            if key
        )
    return keys


def _storage_keys_used_by_other_live_media(keys, collection):
    if not keys:
        return set()

    from apps.media_assets.models import MediaAsset

    references = MediaAsset.objects.exclude(collection=collection).exclude(status="deleted").filter(
        Q(original_file_key__in=keys) | Q(preview_file_key__in=keys) | Q(thumbnail_file_key__in=keys)
    ).values_list("original_file_key", "preview_file_key", "thumbnail_file_key")

    used = set()
    for original_key, preview_key, thumbnail_key in references:
        used.update(key for key in (original_key, preview_key, thumbnail_key) if key in keys)
    return used


def delete_collection(collection):
    from apps.collection_sets.models import CollectionSet
    from apps.media_assets.models import MediaAsset
    from apps.profiles.services import recalculate_user_profile_stats
    from apps.quotas.services import recalculate_storage_usage

    media_assets = list(
        MediaAsset.objects.filter(collection=collection).only(
            "id",
            "collection_id",
            "original_file_key",
            "preview_file_key",
            "thumbnail_file_key",
        )
    )
    storage_keys = _unique_media_storage_keys(media_assets)
    keys_to_delete = storage_keys - _storage_keys_used_by_other_live_media(storage_keys, collection)

    for key in keys_to_delete:
        delete_object(key)

    now = timezone.now()
    with transaction.atomic():
        MediaAsset.objects.filter(collection=collection).update(status="deleted", deleted_at=now, updated_at=now)
        CollectionSet.objects.filter(collection=collection).update(deleted_at=now, updated_at=now)
        collection.deleted_at = now
        collection.save(update_fields=["deleted_at", "updated_at"])

    recalculate_storage_usage(collection.owner)
    recalculate_user_profile_stats(collection.owner)
    return collection
