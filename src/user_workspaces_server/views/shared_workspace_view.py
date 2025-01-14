import json
import logging
from datetime import datetime

from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.exceptions import NotFound, ParseError
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

    def post(self, request):
        # Begin Validity check section
        # Basic validity checks
        try:
            body = json.loads(request.body)
        except Exception as e:
            raise ParseError(f"Invalid JSON: {str(e)}")

        if "shared_user_ids" not in body or "original_workspace_id" not in body:
            raise ParseError("Missing required fields.")

        # Check workspace_id is valid/owned by current user
        try:
            workspace = models.Workspace.objects.get(
                user_id=request.user, id=body["original_workspace_id"]
            )
        except Exception:
            raise NotFound(f"Workspace {body['original_workspace_id']} not found for user.")

        shared_user_ids = body["shared_user_ids"]

        # Check user_ids_to_share are valid
        if not isinstance(shared_user_ids, list):
            raise ParseError("shared_user_ids is not a list.")
        elif len(shared_users := User.objects.filter(pk__in=shared_user_ids)) != len(
            shared_user_ids
        ):
            raise ParseError("Invalid user id provided.")

        # Begin DAO inserts
        # Get latest job for last_params and last_job_type
        try:
            latest_job = models.Job.objects.filter(workspace_id=workspace).latest(
                "datetime_created"
            )
        except Exception:
            latest_job = None

        # Same set of data will be used across all shared_workspace entries
        workspace_data = {
            "name": workspace.name,
            "description": workspace.description,
            "workspace_details": workspace.workspace_details,
            "default_job_type": workspace.default_job_type,
        }

        shared_workspace_data = {
            "original_workspace_id": workspace,
            "shared_workspace_id": None,
            "last_resource_options": {} if latest_job is None else latest_job.resource_options,
            "last_job_type": "" if latest_job is None else latest_job.job_type,
            "is_accepted": False,
        }

        shared_workspaces_created = []
        for user in shared_users:
            # Prepare workspace model creation
            workspace_data_copy = workspace_data.copy()
            workspace_data_copy["user_id"] = user
            workspace_data_copy["datetime_created"] = datetime.now()
            new_workspace = models.Workspace.objects.create(**workspace_data_copy)

            # Create shared workspace mapping
            shared_workspace_data_copy = shared_workspace_data.copy()
            shared_workspace_data_copy["shared_workspace_id"] = new_workspace
            shared_workspace = models.SharedWorkspaceMapping.objects.create(
                **shared_workspace_data_copy
            )
            shared_workspaces_created.append(shared_workspace)

        shared_workspaces_created = serializers.SharedWorkspaceMappingSerializer(
            shared_workspaces_created, many=True
        ).data

        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {
                    "shared_workspaces": shared_workspaces_created,
                },
            }
        )
