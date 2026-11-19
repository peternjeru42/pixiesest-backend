from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.collections.models import Collection
from apps.media_uploads.models import MediaUploadSession
from apps.media_assets.models import MediaAsset
from apps.media_processing.models import MediaProcessingJob
from apps.media_processing.tasks import _finish_asset_if_processing_complete
from apps.quotas.models import StorageQuota
from apps.quotas.services import decrease_storage_usage, increase_storage_usage

from .emails import render_branded_email
from .models import EmailLog
from .tasks import (
    send_collection_invite_email,
    send_first_collection_email,
    send_first_upload_email,
    send_upload_summary_email,
    send_welcome_email,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Droptop <noreply@droptop.app>",
    FRONTEND_URL="https://www.droptop.app",
)
class BrandedEmailTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email="owner@example.com",
            password="password123",
            first_name="Ada",
            business_name="Ada Studio",
        )
        self.collection = Collection.objects.create(
            owner=self.owner,
            title="Autumn Portraits",
            slug="autumn-portraits",
            status="published",
        )

    def test_html_renderer_escapes_dynamic_content(self):
        html = render_branded_email(
            preheader="Preview",
            eyebrow="Gallery",
            heading="<script>alert(1)</script>",
            paragraphs=["Hello <b>client</b>"],
        )

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;client&lt;/b&gt;", html)

    def test_gallery_invite_has_branded_html_and_does_not_expose_a_pin(self):
        log = EmailLog.objects.create(
            owner=self.owner,
            collection=self.collection,
            recipient_email="client@example.com",
            email_type="collection_invite",
        )

        send_collection_invite_email(str(log.id), "Your gallery is ready.")

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.reply_to, [self.owner.email])
        self.assertEqual(email.alternatives[0][1], "text/html")
        self.assertIn("DROPTOP", email.alternatives[0][0])
        self.assertNotIn("Download PIN", email.body)
        log.refresh_from_db()
        self.assertEqual(log.status, "sent")

    def test_welcome_email_explains_the_free_allocation_and_only_sends_once(self):
        send_welcome_email(str(self.owner.id))
        send_welcome_email(str(self.owner.id))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("free 5 GB", mail.outbox[0].subject)
        self.assertIn("Storage included: 5 GB", mail.outbox[0].body)
        self.assertIn("Create your first gallery", mail.outbox[0].body)
        self.assertEqual(EmailLog.objects.filter(email_type="welcome_free_plan").count(), 1)

    def test_first_collection_email_only_sends_for_the_first_collection(self):
        send_first_collection_email(str(self.collection.id))
        send_first_collection_email(str(self.collection.id))
        later_collection = Collection.objects.create(
            owner=self.owner,
            title="Later Gallery",
            slug="later-gallery",
        )
        send_first_collection_email(str(later_collection.id))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("first Droptop collection", mail.outbox[0].subject)
        self.assertIn("Add photos and videos", mail.outbox[0].body)
        self.assertEqual(EmailLog.objects.filter(email_type="first_collection").count(), 1)

    @patch("apps.notifications.tasks.send_first_collection_email.delay")
    def test_creating_a_collection_queues_the_milestone_check(self, delay):
        user = get_user_model().objects.create_user(email="new-collector@example.com", password="password123")
        client = APIClient()
        client.force_authenticate(user)

        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(reverse("collection-list"), {"title": "My First Gallery"}, format="json")

        self.assertEqual(response.status_code, 201)
        delay.assert_called_once_with(response.data["id"])

    def test_first_successful_photo_upload_email_only_sends_once(self):
        first = MediaAsset.objects.create(
            owner=self.owner,
            collection=self.collection,
            media_type="photo",
            original_filename="first.jpg",
            display_filename="first.jpg",
            original_file_key="original/first.jpg",
            mime_type="image/jpeg",
            extension="jpg",
            file_size_bytes=100,
            status="ready",
        )
        send_first_upload_email(str(first.id))
        send_first_upload_email(str(first.id))
        later = MediaAsset.objects.create(
            owner=self.owner,
            collection=self.collection,
            media_type="video",
            original_filename="later.mp4",
            display_filename="later.mp4",
            original_file_key="original/later.mp4",
            mime_type="video/mp4",
            extension="mp4",
            file_size_bytes=200,
            status="ready",
        )
        send_first_upload_email(str(later.id))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("first photo", mail.outbox[0].subject)
        self.assertIn("first.jpg", mail.outbox[0].body)
        self.assertEqual(EmailLog.objects.filter(email_type="first_upload").count(), 1)

    @patch("apps.media_processing.tasks.schedule_owner_stats_refresh")
    @patch("apps.notifications.tasks.send_first_upload_email.delay")
    def test_first_upload_email_is_queued_after_processing_finishes(self, delay, refresh_stats):
        asset = MediaAsset.objects.create(
            owner=self.owner,
            collection=self.collection,
            media_type="photo",
            original_filename="processed.jpg",
            display_filename="processed.jpg",
            original_file_key="original/processed.jpg",
            mime_type="image/jpeg",
            extension="jpg",
            file_size_bytes=100,
            status="processing",
        )
        for job_type in ["photo_preview", "photo_thumbnail", "photo_metadata"]:
            MediaProcessingJob.objects.create(media_asset=asset, job_type=job_type, status="completed")

        with self.captureOnCommitCallbacks(execute=True):
            _finish_asset_if_processing_complete(asset.id)

        asset.refresh_from_db()
        self.assertEqual(asset.status, "ready")
        delay.assert_called_once_with(str(asset.id))
        refresh_stats.assert_called_once_with(asset.owner_id)

    @patch("apps.notifications.views.send_collection_update_email.delay")
    def test_owner_can_notify_each_previous_invite_recipient_once(self, delay):
        EmailLog.objects.create(
            owner=self.owner,
            collection=self.collection,
            recipient_email="client@example.com",
            email_type="collection_invite",
            status="sent",
        )
        EmailLog.objects.create(
            owner=self.owner,
            collection=self.collection,
            recipient_email="client@example.com",
            email_type="collection_invite",
            status="sent",
        )
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.post(
            reverse("collection-notify-update", kwargs={"collection_id": self.collection.id}),
            {"message": "New videos are ready."},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["queued"], 1)
        self.assertEqual(EmailLog.objects.filter(email_type="collection_updated").count(), 1)
        delay.assert_called_once()

    def test_upload_summary_groups_terminal_sessions_and_is_idempotent(self):
        expires_at = timezone.now() + timedelta(hours=1)
        completed = MediaUploadSession.objects.create(
            owner=self.owner,
            collection=self.collection,
            upload_id="upload-complete",
            original_filename="ready.jpg",
            mime_type="image/jpeg",
            file_size_bytes=100,
            r2_object_key="ready.jpg",
            status="completed",
            expires_at=expires_at,
        )
        failed = MediaUploadSession.objects.create(
            owner=self.owner,
            collection=self.collection,
            upload_id="upload-failed",
            original_filename="broken.mov",
            mime_type="video/quicktime",
            file_size_bytes=200,
            r2_object_key="broken.mov",
            status="failed",
            expires_at=expires_at,
        )

        send_upload_summary_email(str(completed.id))
        send_upload_summary_email(str(completed.id))

        completed.refresh_from_db()
        failed.refresh_from_db()
        self.assertIsNotNone(completed.notification_sent_at)
        self.assertIsNotNone(failed.notification_sent_at)
        self.assertEqual(EmailLog.objects.filter(email_type="upload_summary").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("broken.mov", mail.outbox[0].body)

    @patch("apps.notifications.tasks.send_storage_warning_email.delay")
    def test_storage_warning_only_fires_when_crossing_a_threshold(self, delay):
        quota, _ = StorageQuota.objects.update_or_create(
            user=self.owner,
            defaults={"storage_limit_bytes": 1000, "storage_used_bytes": 0},
        )

        with self.captureOnCommitCallbacks(execute=True):
            increase_storage_usage(self.owner, 800, "test")
        with self.captureOnCommitCallbacks(execute=True):
            increase_storage_usage(self.owner, 10, "test")

        self.assertEqual(delay.call_count, 1)
        self.assertEqual(delay.call_args.args[1], 80)

        with self.captureOnCommitCallbacks(execute=True):
            decrease_storage_usage(self.owner, 700, "test")
        quota.refresh_from_db()
        self.assertEqual(quota.storage_warning_level, 0)
        self.assertEqual(quota.storage_warning_cycle, 1)
