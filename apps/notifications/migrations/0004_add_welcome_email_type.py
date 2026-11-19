from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_email_delivery_idempotency"),
    ]

    operations = [
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
                    ("welcome_free_plan", "Welcome to free plan"),
                ],
                max_length=50,
            ),
        ),
    ]
