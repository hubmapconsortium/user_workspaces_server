from django.contrib.auth.models import User
from django.db import models
from rest_framework import serializers


class Workspace(models.Model):
    class Status(models.TextChoices):
        IDLE = "idle"
        ACTIVE = "active"
        DELETING = "deleting"
        ERROR = "error"

    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=64, default="")
    description = models.TextField(default="")
    file_path = models.CharField(max_length=64, default="")
    disk_space = models.BigIntegerField(default=0)
    datetime_created = models.DateTimeField()
    workspace_details = models.JSONField()
    status = models.CharField(max_length=64, default=Status.IDLE, choices=Status.choices)
    default_job_type = models.CharField(max_length=64, null=True)

    def __str__(self):
        return f"{self.id}: {self.user_id.username} - {self.status}"

    @staticmethod
    def get_query_param_fields():
        return ["name", "description", "status"]

    @staticmethod
    def get_dict_fields():
        return [
            "id",
            "name",
            "description",
            "disk_space",
            "datetime_created",
            "workspace_details",
            "status",
            "default_job_type",
        ]


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETE = "complete"
        FAILED = "failed"
        STOPPING = "stopping"

    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    workspace_id = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True)
    resource_job_id = models.IntegerField()
    job_type = models.CharField(max_length=64)
    resource_name = models.CharField(max_length=64)
    status = models.CharField(max_length=64, default=Status.PENDING, choices=Status.choices)
    datetime_created = models.DateTimeField()
    datetime_start = models.DateTimeField(null=True)
    datetime_end = models.DateTimeField(null=True)
    core_hours = models.DecimalField(max_digits=10, decimal_places=5)
    job_details = models.JSONField()
    resource_options = models.JSONField()

    def __str__(self):
        return (
            f"{self.id}: {self.user_id.username if self.user_id else 'User Missing'} - "
            f"Workspace {self.workspace_id.id if self.workspace_id else 'Deleted'} - {self.status}"
        )

    @staticmethod
    def get_query_param_fields():
        return ["workspace_id", "resource_job_id", "job_type", "status"]

    @staticmethod
    def get_dict_fields():
        return [
            "id",
            "workspace_id",
            "resource_job_id",
            "job_type",
            "status",
            "datetime_created",
            "datetime_start",
            "datetime_end",
            "core_hours",
            "job_details",
        ]


class UserQuota(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    max_disk_space = models.IntegerField()
    max_core_hours = models.DecimalField(max_digits=15, decimal_places=5)
    used_disk_space = models.IntegerField()
    used_core_hours = models.DecimalField(max_digits=15, decimal_places=5)


class ExternalUserMapping(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    external_user_id = models.CharField(max_length=128)
    external_username = models.CharField(max_length=64)
    user_authentication_name = models.CharField(max_length=64)
    external_user_details = models.JSONField(blank=True, null=True)

    def __str__(self):
        return (
            f"{self.id}: {self.user_id.username if self.user_id else 'User Missing'} -"
            f" {self.user_authentication_name}"
        )


class SharedWorkspaceMapping(models.Model):
    original_workspace_id = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        related_name="original_workspace_set",
    )
    shared_workspace_id = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="shared_workspace_set"
    )
    last_params = models.JSONField(blank=True, null=True)
    last_job_type = models.CharField(max_length=64, null=True)
    is_accepted = models.BooleanField(default=False)

    @staticmethod
    def get_query_param_fields():
        return ["is_accepted"]

    @staticmethod
    def get_dict_fields():
        return [
            "is_accepted",
            "last_params",
            "last_job_type",
        ]
