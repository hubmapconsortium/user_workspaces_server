# Generated by Django 4.1.2 on 2022-10-27 14:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("user_workspaces_server", "0009_alter_job_status_alter_workspace_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="user_id",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("running", "Running"),
                    ("complete", "Complete"),
                    ("failed", "Failed"),
                    ("stopping", "Stopping"),
                ],
                default="pending",
                max_length=64,
            ),
        ),
    ]
