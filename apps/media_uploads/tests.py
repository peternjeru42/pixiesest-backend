from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.collections.models import Collection
from apps.media_assets.models import MediaAsset

from .models import MediaUploadSession
from .services import cancel_upload, complete_upload
from .tasks import cleanup_expired_uploads


class UploadLifecycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("uploads@example.com", "password")
        self.collection = Collection.objects.create(owner=self.user, title="Upload test", slug="upload-test")

    def create_session(self, *, session_status="pending", asset_status="uploading", expired=False):
        asset = MediaAsset.objects.create(
            owner=self.user,
            collection=self.collection,
            media_type="photo",
            original_filename="photo.jpg",
            display_filename="photo.jpg",
            original_file_key="users/test/photo.jpg",
            mime_type="image/jpeg",
            extension="jpg",
            file_size_bytes=100,
            status=asset_status,
        )
        session = MediaUploadSession.objects.create(
            owner=self.user,
            collection=self.collection,
            media_asset=asset,
            upload_id=f"upload-{asset.id}",
            original_filename="photo.jpg",
            mime_type="image/jpeg",
            file_size_bytes=100,
            r2_object_key=asset.original_file_key,
            status=session_status,
            expires_at=timezone.now() + (-timedelta(minutes=1) if expired else timedelta(hours=1)),
        )
        return session, asset

    @patch("apps.media_uploads.services.delete_object")
    def test_cancel_removes_incomplete_placeholder_and_object(self, delete_object):
        session, asset = self.create_session()

        with self.captureOnCommitCallbacks(execute=True):
            cancel_upload(self.user, session.upload_id)

        session.refresh_from_db()
        asset = MediaAsset.all_objects.get(id=asset.id)
        self.assertEqual(session.status, "cancelled")
        self.assertIsNotNone(asset.deleted_at)
        delete_object.assert_called_once_with(asset.original_file_key)

    @patch("apps.media_uploads.services.queue_media_processing")
    @patch("apps.media_uploads.services.object_exists")
    def test_complete_is_idempotent_after_processing_starts(self, object_exists, queue_media_processing):
        session, _asset = self.create_session(session_status="processing", asset_status="processing")

        completed = complete_upload(self.user, session.upload_id)

        self.assertEqual(completed.id, session.id)
        object_exists.assert_not_called()
        queue_media_processing.assert_not_called()

    @patch("apps.media_uploads.tasks.delete_object")
    def test_cleanup_expires_abandoned_uploads(self, delete_object):
        session, asset = self.create_session(expired=True)

        cleaned = cleanup_expired_uploads()

        session.refresh_from_db()
        asset = MediaAsset.all_objects.get(id=asset.id)
        self.assertEqual(cleaned, 1)
        self.assertEqual(session.status, "expired")
        self.assertIsNotNone(asset.deleted_at)
        delete_object.assert_called_once_with(asset.original_file_key)
