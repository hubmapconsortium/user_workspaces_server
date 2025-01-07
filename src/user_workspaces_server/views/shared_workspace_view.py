import logging

from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user_workspaces_server import models, serializers

logger = logging.getLogger(__name__)


class SharedWorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, shared_workspace_id=None):
        # For a given user we need to return:
        # - The shared workspaces for which they've sent requests
        # - The shared workspaces for which they've received requests
        # We need to filter based on whether they've been accepted or not
        # We need to allow for a single shared workspace to be returned

        original_workspaces = models.SharedWorkspaceMapping.objects.filter(
            original_workspace_id__user_id=request.user
        )

        shared_workspaces = models.SharedWorkspaceMapping.objects.filter(
            shared_workspace_id__user_id=request.user
        )

        if shared_workspace_id:
            shared_workspaces = models.SharedWorkspaceMapping.objects.filter(
                id=shared_workspace_id
            )
        elif params := request.GET:
            for key in set(params.keys()).intersection(
                models.SharedWorkspaceMapping.get_query_param_fields()
            ):
                original_workspaces = original_workspaces.filter(**{key: params[key]})
                shared_workspaces = shared_workspaces.filter(**{key: params[key]})

        original_workspaces = serializers.SharedWorkspaceMappingSerializer(
            original_workspaces, many=True
        ).data
        shared_workspaces = serializers.SharedWorkspaceMappingSerializer(
            shared_workspaces, many=True
        ).data

        response = {
            "message": "Successful.",
            "success": True,
            "data": {"original_workspaces": [], "shared_workspaces": []},
        }

        if original_workspaces or shared_workspaces:
            response["data"]["original_workspaces"] = original_workspaces
            response["data"]["shared_workspaces"] = shared_workspaces
        else:
            response["message"] = "Shared workspace matching given parameters could not be found."

        return JsonResponse(response)
