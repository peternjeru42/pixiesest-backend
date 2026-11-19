from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotas", "0003_migrate_starter_to_free"),
    ]

    operations = [
        migrations.AddField(
            model_name="storagequota",
            name="storage_warning_cycle",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="storagequota",
            name="storage_warning_level",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
