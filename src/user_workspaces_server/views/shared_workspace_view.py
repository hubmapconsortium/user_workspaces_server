import logging

from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user_workspaces_server import models, utils

logger = logging.getLogger(__name__)


class SharedWorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, shared_workspace_id=None):
        shared_workspace = models.SharedWorkspaceMapping.objects.filter(
            shared_workspace_id__user_id=request.user
        )

        if shared_workspace_id:
            shared_workspace = shared_workspace.filter(id=shared_workspace_id)
        elif params := request.GET:
            query_param_fields = models.SharedWorkspaceMapping.get_query_param_fields()
            for key in set(params.keys()).intersection(query_param_fields.keys()):
                query_param_field = query_param_fields[key]
                shared_workspace = shared_workspace.filter(**{query_param_field: params[key]})

        shared_workspaces = list(
            shared_workspace.all().values(*models.SharedWorkspaceMapping.get_dict_fields())
        )

        response = {"message": "Successful.", "success": True, "data": {"shared_workspaces": []}}

        if shared_workspaces:
            response["data"]["shared_workspaces"] = shared_workspaces
        else:
            response["message"] = "Shared workspace matching given parameters could not be found."

        return JsonResponse(response)
