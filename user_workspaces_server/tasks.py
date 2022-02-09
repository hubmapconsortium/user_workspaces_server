from django_q.tasks import async_task
from . import models
import datetime
from user_workspaces_server.controllers.job_types.jupyter_lab_job import JupyterLabJob
from django.apps import apps
from django.conf import settings


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

    job.save()


def queue_job_update(task):
    job_id = list(task.args)[0]

    try:
        job = models.Job.objects.get(pk=job_id)
    except Exception as e:
        print(repr(e))
        raise e

    if job.status in ['pending', 'running']:
        async_task('user_workspaces_server.tasks.update_job_status', job_id, hook='user_workspaces_server.tasks.queue_job_update')
