from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("folders", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="folder",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AddIndex(
            model_name="folder",
            index=models.Index(fields=["owner", "name"], name="folders_fol_owner_i_13814e_idx"),
        ),
    ]
