from django.apps import AppConfig


class CollectionSetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.collection_sets"

    def ready(self):
        import apps.collection_sets.signals  # noqa
