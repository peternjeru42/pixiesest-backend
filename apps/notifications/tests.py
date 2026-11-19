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
from apps.quotas.models import StorageQuota
from apps.quotas.services import decrease_storage_usage, increase_storage_usage

from .emails import render_branded_email
from .models import EmailLog
from .tasks import send_collection_invite_email, send_upload_summary_email


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
