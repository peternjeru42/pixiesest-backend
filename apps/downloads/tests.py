import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .tasks import _generate_zip, cleanup_expired_download_exports


class DownloadTaskTests(SimpleTestCase):
    @patch("apps.downloads.tasks.upload_file")
    @patch("apps.downloads.tasks.download_to_file")
    @patch("apps.downloads.tasks.get_downloadable_assets_for_job")
    @patch("apps.downloads.tasks.DownloadJob.objects")
    def test_generate_zip_uses_disk_backed_uncompressed_archive(
        self,
        objects,
        get_assets,
        download_to_file,
        upload_file,
    ):
        job = SimpleNamespace(
            id="job-id",
            collection_id="collection-id",
            collection=SimpleNamespace(owner_id="owner-id"),
            status="queued",
            started_at=None,
            completed_at=None,
            zip_file_key="",
            file_size_bytes=None,
            save=MagicMock(),
        )
        objects.select_related.return_value.get.return_value = job
        asset = SimpleNamespace(original_file_key="original-key", preview_file_key="preview-key", original_filename="photo.jpg")
        get_assets.return_value.iterator.return_value = iter([asset])
        download_to_file.side_effect = lambda _key, path: Path(path).write_bytes(b"already-compressed-image")

        def inspect_uploaded_archive(_key, path, _content_type):
            with zipfile.ZipFile(path) as archive:
                info = archive.getinfo("photo.jpg")
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(archive.read("photo.jpg"), b"already-compressed-image")

        upload_file.side_effect = inspect_uploaded_archive

        _generate_zip("job-id")

        download_to_file.assert_called_once_with("original-key", download_to_file.call_args.args[1])
        upload_file.assert_called_once()
        self.assertEqual(job.status, "completed")
        self.assertGreater(job.file_size_bytes, 0)

    @patch("apps.downloads.tasks.delete_object")
    @patch("apps.downloads.tasks.DownloadJob.objects")
    def test_cleanup_deletes_export_before_expiring_job(self, objects, delete_object):
        job = SimpleNamespace(
            id="job-id",
            zip_file_key="exports/job.zip",
            status="completed",
            save=MagicMock(),
        )
        objects.filter.return_value.exclude.return_value.iterator.return_value = iter([job])

        cleaned = cleanup_expired_download_exports()

        delete_object.assert_called_once_with("exports/job.zip")
        self.assertEqual(cleaned, 1)
        self.assertEqual(job.status, "expired")
        self.assertEqual(job.zip_file_key, "")
