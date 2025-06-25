import datetime
import logging
import os
import shutil

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.apps import apps
from django.conf import settings
from django.db.models import Sum
from django.template.loader import render_to_string
from django_q.brokers import get_broker
from django_q.tasks import async_task

from . import models, utils

logger = logging.getLogger(__name__)


def update_job_status(job_id):
    logger.info(f"Updating job {job_id} status on {get_broker().list_key}")
    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    resource = apps.get_app_config("user_workspaces_server").main_resource
    resource_job_info = resource.get_resource_job(job)
    current_job_status = resource_job_info["status"]

    # Check the existing job status
    # If the job is STOPPING, FAILED, or COMPLETE
    # Status should only ever be one of the following:
    # pending, running, complete, failed, stopping

    job.refresh_from_db()

    if current_job_status == models.Job.Status.RUNNING and job.datetime_start is None:
        job.datetime_start = datetime.datetime.now(job.datetime_created.tzinfo)
        time_pending = (job.datetime_start - job.datetime_created).total_seconds()
        job.job_details["metrics"]["time_pending"] = time_pending
    elif current_job_status in [models.Job.Status.COMPLETE, models.Job.Status.FAILED]:
        job.datetime_end = datetime.datetime.now()
    elif current_job_status == models.Job.Status.PENDING:
        current_time_pending = (
            datetime.datetime.now(job.datetime_created.tzinfo) - job.datetime_created
        ).total_seconds()
        time_pending_catch = resource.config.get("time_pending_catch")
        if int(time_pending_catch) and current_time_pending > time_pending_catch:
            logger.error(
                f"Job {job_id} for user {job.user_id.username} has been pending more than {time_pending_catch}"
            )

    if current_job_status == models.Job.Status.FAILED:
        logger.error(f"Job {job_id} for user {job.user_id.username} has failed.")

    job.status = (
        job.status
        if (
            job.status == models.Job.Status.STOPPING
            and current_job_status not in [models.Job.Status.COMPLETE, models.Job.Status.FAILED]
        )
        else current_job_status
    )

    try:
        job_type_config = apps.get_app_config("user_workspaces_server").available_job_types.get(
            job.job_type
        )

        job_type = utils.generate_controller_object(
            job_type_config["job_type"],
            "jobtypes",
            {
                "config": job_type_config["environment_details"][
                    settings.UWS_CONFIG["main_resource"]
                ],
                "job_details": job,
            },
        )
    except Exception:
        raise Exception("Invalid job type specified")

    # TODO: Make sure that we're using the resource to do this type of status check
    job_status = job_type.status_check(job)

    job.job_details["current_job_details"].update(job_status.get("current_job_details", {}))
    job.job_details["metrics"].update(job_status.get("metrics", {}))

    # TODO: At some point we will have metrics returned by resource_job_info
    job.job_details["current_job_details"].update(resource_job_info.get("current_job_details", {}))

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

    if job.status in [
        models.Job.Status.PENDING,
        models.Job.Status.RUNNING,
        models.Job.Status.STOPPING,
    ]:
        async_task(
            "user_workspaces_server.tasks.update_job_status",
            job_id,
            hook="user_workspaces_server.tasks.queue_job_update",
        )
    elif job.status in [models.Job.Status.COMPLETE, models.Job.Status.FAILED]:
        workspace = job.workspace_id
        if (
            not models.Job.objects.filter(
                workspace_id=job.workspace_id,
                status__in=[models.Job.Status.PENDING, models.Job.Status.RUNNING],
            ).exists()
            and workspace.status != models.Workspace.Status.DELETING
        ):
            workspace.status = models.Workspace.Status.IDLE
            workspace.save()
            async_update_workspace(workspace.pk)
            async_task(
                "user_workspaces_server.tasks.update_job_core_hours",
                job_id,
                cluster="myproject",
            )


def update_job_core_hours(job_id):
    logger.info(f"Updating job {job_id} core hours on {get_broker().list_key}")
    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    resource = apps.get_app_config("user_workspaces_server").main_resource
    job.core_hours = resource.get_job_core_hours(job)
    job.save()
    user_quota = models.UserQuota.objects.filter(user_id=job.workspace_id.user_id).first()

    # If this user has a quota spawn a routine to update the core hours.
    if user_quota:
        async_task("user_workspaces_server.tasks.update_user_quota_core_hours", user_quota.id)


def stop_job(job_id):
    logger.info(f"Stopping job {job_id} on {get_broker().list_key}")
    try:
        job = models.Job.objects.get(pk=job_id)
    except models.Job.DoesNotExist:
        logger.exception(f"Job {job_id} does not exist.")
        raise

    resource = apps.get_app_config("user_workspaces_server").main_resource
    if not resource.stop_job(job):
        job.status = models.Job.Status.FAILED
        job.save()


def delete_workspace(workspace_id):
    logger.info(f"Deleting workspace {workspace_id} on {get_broker().list_key}")
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
        async_task("user_workspaces_server.tasks.update_user_quota_disk_space", user_quota.id)


def async_update_workspace(workspace_id: int):
    # Helper that makes sure updates go to the "long" cluster
    async_task("user_workspaces_server.tasks.update_workspace", workspace_id, cluster="long")


def update_workspace(workspace_id: int):
    logger.info(f"Updating workspace {workspace_id} on {get_broker().list_key}")
    try:
        workspace = models.Workspace.objects.get(pk=workspace_id)
    except models.Workspace.DoesNotExist:
        logger.exception(f"Workspace {workspace_id} does not exist.")
        raise

    main_storage = apps.get_app_config("user_workspaces_server").main_storage
    current_details = {"files": [], "symlinks": []}

    # This will IGNORE dot directories and files
    for dirpath, dirnames, filenames, dirfd in main_storage.get_dir_tree(workspace.file_path):
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
            current_details["symlinks" if os.path.islink(file_path) else "files"].append(
                {"name": relative_path}
            )

    workspace.workspace_details["current_workspace_details"] = current_details

    dir_size = main_storage.get_dir_size(workspace.file_path)
    workspace.disk_space = dir_size
    workspace.save()

    user_quota = models.UserQuota.objects.filter(user_id=workspace.user_id).first()
    # If this user has a quota spawn a routine to update the disk space.
    if user_quota:
        async_task("user_workspaces_server.tasks.update_user_quota_disk_space", user_quota.id)


def update_user_quota_disk_space(user_quota_id):
    logger.info(f"Updating user quota {user_quota_id} disk space on {get_broker().list_key}")
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
    logger.info(f"Updating user quota {user_quota_id} core hours on {get_broker().list_key}")
    try:
        user_quota = models.UserQuota.objects.get(pk=user_quota_id)
    except models.UserQuota.DoesNotExist:
        logger.exception(f"UserQuota {user_quota_id} does not exist.")
        raise

    user_quota.used_core_hours = models.Job.objects.filter(
        workspace_id__user_id=user_quota.user_id
    ).aggregate(Sum("core_hours"))["core_hours__sum"]
    user_quota.save()


def initialize_shared_workspace(shared_workspace_mapping_id: int):
    shared_workspace_mapping = models.SharedWorkspaceMapping.objects.get(
        pk=shared_workspace_mapping_id
    )
    original_workspace = shared_workspace_mapping.original_workspace_id
    shared_workspace = shared_workspace_mapping.shared_workspace_id

    main_storage = apps.get_app_config("user_workspaces_server").main_storage
    external_user_mapping = main_storage.storage_user_authentication.has_permission(
        shared_workspace.user_id
    )

    # Set the shared_workspace file path
    shared_workspace.file_path = os.path.join(
        external_user_mapping.external_username, str(shared_workspace.pk)
    )

    try:
        # Copy non . directories
        shutil.copytree(
            os.path.join(main_storage.root_dir, original_workspace.file_path),
            os.path.join(main_storage.root_dir, shared_workspace.file_path),
            ignore=shutil.ignore_patterns(".*"),
            symlinks=True,
        )
        main_storage.set_ownership(
            shared_workspace.file_path, external_user_mapping, recursive=True
        )
    except Exception as e:
        logger.exception(f"Copying files for {shared_workspace_mapping} failed: {e}")

    async_update_workspace(shared_workspace.pk)

    message = render_to_string(
        "email_templates/share_email.txt",
        context={
            "sharer": original_workspace.user_id,
            "receiver": shared_workspace.user_id,
            "mapping_details": shared_workspace_mapping,
            "original_workspace": original_workspace,
        },
    )
    async_task(
        "django.core.mail.send_mail",
        "Invitation to Share a Workspace",
        message,
        None,
        [shared_workspace.user_id.email],
    )

    # TODO: Set shared_workspace status to idle
    shared_workspace.status = "idle"
    shared_workspace.save()


def check_main_storage_user(user):
    main_storage = apps.get_app_config("user_workspaces_server").main_storage

    external_user_mapping = main_storage.storage_user_authentication.has_permission(user)

    if not external_user_mapping:
        logger.exception(f"User {user} could not be authenticated on {main_storage}.")
        raise
