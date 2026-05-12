import mimetypes
import re
from pathlib import Path

from django.utils.crypto import get_random_string
from django.utils.text import slugify


def unique_slugify(instance, value, slug_field="slug", queryset=None):
    base_slug = slugify(value)[:80] or get_random_string(8).lower()
    slug = base_slug
    queryset = queryset or instance.__class__.objects.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    counter = 2
    while queryset.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def extension_from_filename(filename):
    return Path(filename).suffix.lower().lstrip(".")


def safe_filename(filename):
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)


def mime_type_from_filename(filename):
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def human_file_size(num_bytes):
    value = float(num_bytes or 0)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
