from django.contrib import admin

from user_workspaces_server import models

# Register your models here.
admin.site.register(
    [models.ExternalUserMapping, models.UserQuota, models.Workspace, models.Job]
)
