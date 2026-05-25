from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.media_assets.models import MediaAsset
from apps.media_processing.tasks import process_uploaded_media


class Command(BaseCommand):
    help = "Queue or run video processing for existing videos missing previews or metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reprocess every existing video, including videos that already have thumbnails and metadata.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run processing immediately in this process instead of queueing Celery tasks.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of videos to process. Defaults to all matching videos.",
        )

    def handle(self, *args, **options):
        queryset = MediaAsset.objects.filter(media_type="video").exclude(status="deleted")
        if not options["all"]:
            queryset = queryset.filter(
                Q(thumbnail_file_key="")
                | Q(duration_seconds__isnull=True)
                | Q(original_width__isnull=True)
                | Q(original_height__isnull=True)
            )

        queryset = queryset.order_by("created_at").only(
            "id",
            "display_filename",
            "thumbnail_file_key",
            "duration_seconds",
            "original_width",
            "original_height",
        )
        if options["limit"] > 0:
            queryset = queryset[: options["limit"]]

        processed = 0
        for asset in queryset.iterator():
            if options["sync"]:
                process_uploaded_media(str(asset.id))
            else:
                process_uploaded_media.delay(str(asset.id))
            processed += 1
            self.stdout.write(f"Queued video preview backfill for {asset.display_filename} ({asset.id})")

        if processed == 0:
            self.stdout.write(self.style.SUCCESS("No existing videos need preview backfill."))
            return

        mode = "processed" if options["sync"] else "queued"
        self.stdout.write(self.style.SUCCESS(f"Successfully {mode} {processed} existing video(s)."))
