from django.db import migrations


def migrate_starter_quotas(apps, schema_editor):
    StorageQuota = apps.get_model("quotas", "StorageQuota")
    StorageQuota.objects.filter(plan_name="starter").update(
        plan_name="free",
        storage_limit_bytes=5 * 1024**3,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("quotas", "0002_alter_storagequota_plan_name_and_more"),
    ]

    operations = [migrations.RunPython(migrate_starter_quotas, migrations.RunPython.noop)]
