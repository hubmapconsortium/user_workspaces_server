# Generated by Django 3.2.12 on 2022-04-08 17:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_workspaces_server", "0005_alter_job_datetime_start"),
    ]

    operations = [
        migrations.AddField(
            model_name="externalusermapping",
            name="external_user_details",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
