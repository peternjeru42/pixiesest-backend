from django.db import migrations, models
from django.utils import timezone


def mark_existing_sessions_notified(apps, schema_editor):
    MediaUploadSession = apps.get_model("media_uploads", "MediaUploadSession")
    MediaUploadSession.objects.update(notification_sent_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("media_uploads", "0002_allow_collection_level_uploads"),
    ]

    operations = [
        migrations.AddField(
            model_name="mediauploadsession",
            name="notification_sent_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(mark_existing_sessions_notified, migrations.RunPython.noop),
    ]
