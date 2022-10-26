# Generated by Django 3.2.9 on 2021-12-09 18:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ExternalUserMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("external_user_id", models.IntegerField()),
                ("external_username", models.CharField(max_length=64)),
                ("user_authentication_name", models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="UserQuota",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("max_disk_space", models.IntegerField()),
                ("max_core_hours", models.IntegerField()),
                ("used_disk_space", models.IntegerField()),
                ("used_core_hours", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="Workspace",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(default="", max_length=64)),
                ("description", models.TextField(default="")),
                ("file_path", models.CharField(default="", max_length=64)),
                ("disk_space", models.IntegerField(default=0)),
                ("datetime_created", models.DateTimeField()),
                ("workspace_details", models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("job_type", models.CharField(max_length=64)),
                ("resource_name", models.CharField(max_length=64)),
                ("status", models.CharField(max_length=64)),
                ("datetime_start", models.DateTimeField()),
                ("datetime_end", models.DateTimeField(null=True)),
                ("core_hours", models.IntegerField(default=0)),
                ("job_details", models.JSONField()),
                (
                    "workspace_id",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="user_workspaces_server.workspace",
                    ),
                ),
            ],
        ),
    ]
