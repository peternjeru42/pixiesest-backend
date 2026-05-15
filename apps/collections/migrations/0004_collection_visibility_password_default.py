from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("collections", "0003_collectiondownloadsettings_download_pin_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collection",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("public", "Public"),
                    ("password_protected", "Password protected"),
                    ("private", "Private"),
                    ("unlisted", "Unlisted"),
                ],
                db_index=True,
                default="password_protected",
                max_length=30,
            ),
        ),
    ]
