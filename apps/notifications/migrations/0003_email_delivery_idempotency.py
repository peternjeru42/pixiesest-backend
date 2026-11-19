from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_emaillog_read_at_and_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="emaillog",
            name="dedupe_key",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="notificationtemplate",
            name="template_type",
            field=models.CharField(
                choices=[
                    ("collection_invite", "Collection invite"),
                    ("download_zip_ready", "Download ZIP ready"),
                    ("favorite_list_submitted", "Favorite list submitted"),
                    ("password_reset", "Password reset"),
                    ("email_verification", "Email verification"),
                    ("upload_summary", "Upload summary"),
                    ("collection_updated", "Collection updated"),
                    ("billing_receipt", "Billing receipt"),
                    ("payment_failed", "Payment failed"),
                    ("storage_warning", "Storage warning"),
                ],
                max_length=50,
            ),
        ),
    ]
