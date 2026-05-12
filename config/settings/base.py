import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "unsafe-local-development-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.profiles.apps.ProfilesConfig",
    "apps.quotas.apps.QuotasConfig",
    "apps.folders.apps.FoldersConfig",
    "apps.collections.apps.CollectionsConfig",
    "apps.collection_sets.apps.CollectionSetsConfig",
    "apps.storage.apps.StorageConfig",
    "apps.media_assets.apps.MediaAssetsConfig",
    "apps.media_uploads.apps.MediaUploadsConfig",
    "apps.media_processing.apps.MediaProcessingConfig",
    "apps.gallery_access.apps.GalleryAccessConfig",
    "apps.public_gallery.apps.PublicGalleryConfig",
    "apps.favorites.apps.FavoritesConfig",
    "apps.downloads.apps.DownloadsConfig",
    "apps.activity.apps.ActivityConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.admin_dashboard.apps.AdminDashboardConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/pixieset"),
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "20/minute",
        "gallery_verify": "20/minute",
        "download_pin": "10/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "30"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(env("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Pixieset-style Client Gallery API",
    "DESCRIPTION": "REST API for photographer galleries, proofing, downloads, and storage.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CELERY_BROKER_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

CLOUDFLARE_R2_ACCOUNT_ID = env("CLOUDFLARE_R2_ACCOUNT_ID", "")
CLOUDFLARE_R2_ACCESS_KEY_ID = env("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
CLOUDFLARE_R2_SECRET_ACCESS_KEY = env("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
CLOUDFLARE_R2_BUCKET_NAME = env("CLOUDFLARE_R2_BUCKET_NAME", "")
CLOUDFLARE_R2_ENDPOINT_URL = env("CLOUDFLARE_R2_ENDPOINT_URL", "")
CLOUDFLARE_R2_PUBLIC_BASE_URL = env("CLOUDFLARE_R2_PUBLIC_BASE_URL", "")
R2_SIGNED_URL_EXPIRES_SECONDS = int(env("R2_SIGNED_URL_EXPIRES_SECONDS", "900"))

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@example.com")

MAX_UPLOAD_FILE_SIZE_BYTES = int(env("MAX_UPLOAD_FILE_SIZE_BYTES", str(5 * 1024**3)))
ALLOWED_UPLOAD_MIME_TYPES = env_list(
    "ALLOWED_UPLOAD_MIME_TYPES",
    "image/jpeg,image/png,image/webp,image/gif,image/tiff,video/mp4,video/quicktime",
)
