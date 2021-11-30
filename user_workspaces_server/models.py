from django.db import models


class Workspace(models.Model):
    name = models.CharField(max_length=64, default="")
    description = models.TextField(default="")
    file_path = models.CharField(max_length=64, default="")
    disk_space = models.IntegerField(default=0)
    datetime_created = models.DateTimeField()
    workspace_details = models.JSONField()


class Job(models.Model):
    workspace_id = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True)
    job_type = models.CharField(max_length=64)
    resource_name = models.CharField(max_length=64)
    status = models.CharField(max_length=64)
    datetime_start = models.DateTimeField()
    datetime_end = models.DateTimeField(null=True)
    core_hours = models.IntegerField(default=0)
    job_details = models.JSONField()


class UserQuota(models.Model):
    max_disk_space = models.IntegerField()
    max_core_hours = models.IntegerField()
    used_disk_space = models.IntegerField()
    used_core_hours = models.IntegerField()


class ExternalUserMapping(models.Model):
    external_user_id = models.IntegerField()
    external_username = models.CharField(max_length=64)
    user_authentication_name = models.CharField(max_length=64)
