import datetime
import logging
import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.apps import apps
from django.conf import settings
from django.db.models import Sum
from django_q.tasks import async_task

from user_workspaces_server.controllers.job_types.jupyter_lab_job import \
    JupyterLabJob

from . import models

logger = logging.getLogger(__name__)


def update_job_status(job_id):
    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    resource = apps.get_app_config("user_workspaces_server").main_resource
    resource_job_info = resource.get_resource_job(job)
    job.status = resource_job_info["status"]

    # Status should only ever be one of the following:
    # pending, running, complete, failed
    if job.status == models.Job.Status.RUNNING and job.datetime_start is None:
        job.datetime_start = datetime.datetime.now()
    elif job.status in [models.Job.Status.COMPLETE, models.Job.Status.FAILED]:
        job.datetime_end = datetime.datetime.now()

    # TODO: Initialize appropriate JobType
    job_type = JupyterLabJob(
        settings.UWS_CONFIG["available_job_types"]["jupyter_lab"][
            "environment_details"
        ][settings.UWS_CONFIG["main_resource"]],
        job,
    )

    # TODO: Make sure that we're using the resource to do this type of status check
    job.job_details["current_job_details"].update(job_type.status_check(job))

    if job.job_details["current_job_details"].get("connection_details", {}):
        job.job_details["current_job_details"]["connection_details"][
            "url_domain"
        ] = resource.passthrough_domain

    job.save()

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"job_status_{job_id}",
        {
            "type": "job_status_update",
            "message": {
                "status": job.status,
                "current_job_details": job.job_details["current_job_details"],
            },
        },
    )


def queue_job_update(task):
    job_id = list(task.args)[0]

    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    if job.status in [models.Job.Status.PENDING, models.Job.Status.RUNNING]:
        async_task(
            "user_workspaces_server.tasks.update_job_status",
            job_id,
            hook="user_workspaces_server.tasks.queue_job_update",
        )
    elif job.status in [models.Job.Status.COMPLETE, models.Job.Status.FAILED]:
        workspace = job.workspace_id
        if not models.Job.objects.filter(
            workspace_id=job.workspace_id,
            status__in=[models.Job.Status.PENDING, models.Job.Status.RUNNING],
        ).exists():
            workspace.status = models.Workspace.Status.IDLE
            workspace.save()
            async_task("user_workspaces_server.tasks.update_workspace", workspace.id)
            async_task("user_workspaces_server.tasks.update_job_core_hours", job_id)


def update_job_core_hours(job_id):
    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    resource = apps.get_app_config("user_workspaces_server").main_resource
    job.core_hours = resource.get_job_core_hours(job)
    job.save()
    user_quota = models.UserQuota.objects.filter(
        user_id=job.workspace_id.user_id
    ).first()

    # If this user has a quota spawn a routine to update the core hours.
    if user_quota:
        async_task(
            "user_workspaces_server.tasks.update_user_quota_core_hours", user_quota.id
        )


def delete_workspace(workspace_id):
    try:
        workspace = models.Workspace.objects.get(pk=workspace_id)
    except models.Workspace.DoesNotExist:
        logger.exception(f"Workspace {workspace_id} does not exist.")
        raise

    main_storage = apps.get_app_config("user_workspaces_server").main_storage
    external_user_mapping = main_storage.storage_user_authentication.has_permission(
        workspace.user_id
    )

    try:
        main_storage.delete_dir(workspace.file_path, external_user_mapping)
    except Exception:
        workspace.status = models.Workspace.Status.ERROR
        workspace.save()
        logger.exception(f"Could not delete workspace {workspace_id}")
        raise

    workspace.delete()

    user_quota = models.UserQuota.objects.filter(user_id=workspace.user_id).first()
    # If this user has a quota spawn a routine to update the disk space.
    if user_quota:
        async_task(
            "user_workspaces_server.tasks.update_user_quota_disk_space", user_quota.id
        )


def update_workspace(workspace_id):
    try:
        workspace = models.Workspace.objects.get(pk=workspace_id)
    except models.Workspace.DoesNotExist:
        logger.exception(f"Workspace {workspace_id} does not exist.")
        raise

    main_storage = apps.get_app_config("user_workspaces_server").main_storage
    current_details = {"files": [], "symlinks": []}

    # This will IGNORE dot directories and files
    for dirpath, dirnames, filenames, dirfd in main_storage.get_dir_tree(
        workspace.file_path
    ):
        dirnames[:] = [dirname for dirname in dirnames if not dirname[0] == "."]
        filenames = [f for f in filenames if not f[0] == "."]

        for symlink in dirnames:
            symlink_path = os.path.join(dirpath, symlink)
            if os.path.islink(symlink_path):
                relative_path = symlink_path.replace(
                    os.path.join(main_storage.root_dir, workspace.file_path), ""
                )
                current_details["symlinks"].append({"name": relative_path})

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            relative_path = file_path.replace(
                os.path.join(main_storage.root_dir, workspace.file_path), ""
            )
            current_details[
                "symlinks" if os.path.islink(file_path) else "files"
            ].append({"name": relative_path})

    workspace.workspace_details["current_workspace_details"] = current_details

    dir_size = main_storage.get_dir_size(workspace.file_path)
    workspace.disk_space = dir_size
    workspace.save()

    user_quota = models.UserQuota.objects.filter(user_id=workspace.user_id).first()
    # If this user has a quota spawn a routine to update the disk space.
    if user_quota:
        async_task(
            "user_workspaces_server.tasks.update_user_quota_disk_space", user_quota.id
        )


def update_user_quota_disk_space(user_quota_id):
    try:
        user_quota = models.UserQuota.objects.get(pk=user_quota_id)
    except models.UserQuota.DoesNotExist:
        logger.exception(f"UserQuota {user_quota_id} does not exist.")
        raise

    user_quota.used_disk_space = models.Workspace.objects.filter(
        user_id=user_quota.user_id
    ).aggregate(Sum("disk_space"))["disk_space__sum"]
    user_quota.save()


def update_user_quota_core_hours(user_quota_id):
    try:
        user_quota = models.UserQuota.objects.get(pk=user_quota_id)
    except models.UserQuota.DoesNotExist:
        logger.exception(f"UserQuota {user_quota_id} does not exist.")
        raise

    user_quota.used_core_hours = models.Job.objects.filter(
        workspace_id__user_id=user_quota.user_id
    ).aggregate(Sum("core_hours"))["core_hours__sum"]
    user_quota.save()
