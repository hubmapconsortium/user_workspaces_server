# Generated by Django 4.1.2 on 2024-07-23 20:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_workspaces_server", "0011_workspace_default_job_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="resource_options",
            field=models.JSONField(default={}),
            preserve_default=False,
        ),
    ]
