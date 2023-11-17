import logging

from django.http import JsonResponse
from django_q.tasks import async_task
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user_workspaces_server import models
from user_workspaces_server.exceptions import WorkspaceClientException

logger = logging.getLogger(__name__)


class JobView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id=None):
        job = models.Job.objects.filter(workspace_id__user_id=request.user)

        if job_id:
            job = job.filter(id=job_id)
        elif params := request.GET:
            for key in set(params.keys()).intersection(
                set(models.Job.get_query_param_fields())
            ):
                job = job.filter(**{key: params[key]})

        job = list(job.all().values(*models.Job.get_dict_fields()))

        if job:
            return JsonResponse(
                {"message": "Successful.", "success": True, "data": {"jobs": job}}
            )
        else:
            raise NotFound(f"Job matching given parameters could not be found.")

    def put(self, request, job_id, put_type):
        try:
            job = models.Job.objects.get(workspace_id__user_id=request.user, id=job_id)
        except models.Job.DoesNotExist:
            raise NotFound(f"Job {job_id} not found for user.")

        if put_type.lower() == "stop":
            if job.resource_job_id == -1:
                job.status = models.Job.Status.COMPLETE
                job.save()
                return JsonResponse({"message": "Successful stop.", "success": True})

            if job.status in [
                models.Job.Status.COMPLETE,
                models.Job.Status.FAILED,
                models.Job.Status.STOPPING,
            ]:
                raise WorkspaceClientException("This job is not running or pending.")

            job.status = models.Job.Status.STOPPING
            job.save()
            async_task("user_workspaces_server.tasks.stop_job", job.pk)
            return JsonResponse({"message": "Job queued to stop.", "success": True})
        else:
            raise WorkspaceClientException("Invalid PUT type passed.")
