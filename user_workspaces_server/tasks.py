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

    resource = apps.get_app_config('user_workspaces_server').available_resources['local_resource']
    resource_job_info = resource.get_job(job.resource_job_id)
    job.status = resource_job_info['status']

    if job.status == 'running' and job.datetime_start is None:
        job.datetime_start = datetime.datetime.now()
    elif job.status in ['zombie', 'complete']:
        job.datetime_end = datetime.datetime.now()

    # TODO: Initialize appropriate JobType
    job_type = JupyterLabJob(
        settings.CONFIG['available_job_types']['jupyter_lab']['environment_details']['local_resource'], job)

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

    if job.status in ['pending', 'running', 'sleeping']:
        async_task('user_workspaces_server.tasks.update_job_status', job_id,
                   hook='user_workspaces_server.tasks.queue_job_update')
