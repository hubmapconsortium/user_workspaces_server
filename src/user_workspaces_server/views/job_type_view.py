import logging

from django.http import JsonResponse
from rest_framework.views import APIView

from user_workspaces_server.apps import UserWorkspacesServerConfig

logger = logging.getLogger(__name__)

config = UserWorkspacesServerConfig

class JobTypeView(APIView):
    def get(self, request):
        job_types = {}
        for job_type_id, job_type_dict in config.available_job_types.items():
            job_types[job_type_id] = {"id": job_type_id, "name": job_type_dict["name"]}

        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {"job_types": job_types},
            }
        )
