from django_q.tasks import async_task
from . import models
import datetime
from user_workspaces_server.controllers.job_types.jupyter_lab_job import JupyterLabJob
from django.apps import apps
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def update_job_status(job_id):
    try:
        job = models.Job.objects.get(pk=job_id)
    except Exception as e:
        print(repr(e))
        raise e

    resource = apps.get_app_config('user_workspaces_server').main_resource
    resource_job_info = resource.get_resource_job(job)
    job.status = resource_job_info['status']

    # Status should only ever be one of the following:
    # pending, running, complete, failed
    if job.status == 'running' and job.datetime_start is None:
        job.datetime_start = datetime.datetime.now()
    elif job.status in ['complete', 'failed']:
        job.datetime_end = datetime.datetime.now()

    # TODO: Initialize appropriate JobType
    job_type = JupyterLabJob(
        settings.CONFIG['available_job_types']['jupyter_lab']['environment_details'][settings.CONFIG['main_resource']],
        job)

    # TODO: Make sure that we're using the resource to do this type of status check
    job.job_details['current_job_details'].update(job_type.status_check(job))

    if job.job_details['current_job_details'].get('connection_details', {}):
        job.job_details['current_job_details']['connection_details']['url_domain'] = \
            resource.passthrough_domain

    job.save()

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(f'job_status_{job_id}', {
        "type": "job_status_update",
        "message": {
            'status': job.status,
            'current_job_details': job.job_details['current_job_details']
        }
    })


def queue_job_update(task):
    job_id = list(task.args)[0]

    try:
        job = models.Job.objects.get(pk=job_id)
    except Exception as e:
        print(repr(e))
        raise e

    if job.status in ['pending', 'running']:
        async_task('user_workspaces_server.tasks.update_job_status', job_id,
                   hook='user_workspaces_server.tasks.queue_job_update')
    elif job.status in ['completed', 'failed']:
        workspace = job.workspace_id
        if not models.Job.objects.filter(workspace_id=job.workspace_id, status__in=['pending', 'running']).exists():
            workspace.status = 'idle'
            workspace.save()


def delete_workspace(workspace_id):
    # Might want to make this a background task since it might be a massive directory.
    try:
        workspace = models.Workspace.objects.get(pk=workspace_id)
    except Exception as e:
        print(repr(e))
        raise e

    main_storage = apps.get_app_config('user_workspaces_server').main_storage
    main_storage.delete_dir(workspace.file_path)

    workspace.delete()

    # TODO: Update the user quota, this can be done in the background
