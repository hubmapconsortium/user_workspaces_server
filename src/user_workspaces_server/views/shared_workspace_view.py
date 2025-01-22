import json
import logging
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import User
from django.http import JsonResponse
from django_q.tasks import async_task
from rest_framework.exceptions import APIException, NotFound, ParseError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user_workspaces_server import models, serializers
from user_workspaces_server.exceptions import WorkspaceClientException

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
            shared_workspaces = shared_workspaces.filter(
                shared_workspace_id__pk=shared_workspace_id
            )
            original_workspaces = original_workspaces.filter(
                shared_workspace_id__pk=shared_workspace_id
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

        for user in shared_users:
            # Check whether user has permission
            main_storage = apps.get_app_config("user_workspaces_server").main_storage
            if not main_storage.storage_user_authentication.has_permission(user):
                raise WorkspaceClientException(
                    f"User {user.first_name} {user.last_name} does not have permission on the file system."
                )

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
            "datetime_created": datetime.now(),
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
            new_workspace = models.Workspace.objects.create(**workspace_data_copy)

            # Create shared workspace mapping
            shared_workspace_data_copy = shared_workspace_data.copy()
            shared_workspace_data_copy["shared_workspace_id"] = new_workspace
            shared_workspace_data_copy["datetime_share_created"] = datetime.now()
            shared_workspace = models.SharedWorkspaceMapping.objects.create(
                **shared_workspace_data_copy
            )
            shared_workspaces_created.append(shared_workspace)

        for shared_workspace_created in shared_workspaces_created:
            logger.info(
                f"Shared workspace created, sending to initialize: {shared_workspace_created}"
            )
            async_task(
                "user_workspaces_server.tasks.initialize_shared_workspace",
                shared_workspace_created.pk,
                cluster="long",
            )

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

    def put(self, request, shared_workspace_id, put_type):
        # Basic validation checks
        try:
            shared_workspace_mapping = models.SharedWorkspaceMapping.objects.get(
                shared_workspace_id=shared_workspace_id,
                shared_workspace_id__user_id=request.user,
            )
        except Exception:
            raise NotFound(f"Shared workspace {shared_workspace_id} not found.")

        if put_type == "accept":
            # Set is_accepted to true for shared_workspace_id
            shared_workspace_mapping.is_accepted = True
            shared_workspace_mapping.save()

            # Update the created timestamp for the workspace once they accept the request
            shared_workspace = shared_workspace_mapping.shared_workspace_id
            shared_workspace.datetime_created = datetime.now()
            shared_workspace.save()
        else:
            raise NotFound(f"Put type {put_type} not supported.")

        return JsonResponse({"message": "Successful.", "success": True})

    def delete(self, request, shared_workspace_id):
        # Basic validation checks

        # Check that the workspace exists
        try:
            shared_workspace_mapping = models.SharedWorkspaceMapping.objects.get(
                shared_workspace_id__pk=shared_workspace_id
            )
        except models.SharedWorkspaceMapping.DoesNotExist:
            raise NotFound(f"Shared workspace {shared_workspace_id} not found.")

        # Check ownership of either original workspace or shared workspace
        if request.user not in [
            shared_workspace_mapping.shared_workspace_id.user_id,
            shared_workspace_mapping.original_workspace_id.user_id,
        ]:
            raise PermissionDenied(
                f"User does not have permissions for shared workspace {shared_workspace_id}"
            )

        shared_workspace = shared_workspace_mapping.shared_workspace_id

        # Check that the workspace hasn't been accepted
        if shared_workspace.is_accepted:
            raise WorkspaceClientException(
                f"Shared workspace {shared_workspace_id} has been accepted and cannot be deleted."
            )

        if models.Job.objects.filter(
            workspace_id=shared_workspace.shared_workspace_id, status__in=["pending", "running"]
        ).exists():
            raise WorkspaceClientException(
                "Cannot delete workspace, jobs are running for this workspace."
            )

        main_storage = apps.get_app_config("user_workspaces_server").main_storage
        external_user_mapping = main_storage.storage_user_authentication.has_permission(
            request.user
        )

        if not external_user_mapping:
            raise WorkspaceClientException(
                "User could not be found/created on main storage system."
            )

        if not main_storage.is_valid_path(shared_workspace.file_path):
            logger.error(f"Workspace {shared_workspace.pk} deletion failed due to invalid path")
            shared_workspace.status = models.Workspace.Status.ERROR
            shared_workspace.save()
            raise APIException(
                "Please contact a system administrator there is a failure with "
                "the workspace directory that will not allow for this workspace to be deleted."
            )

        shared_workspace.status = models.Workspace.Status.DELETING
        shared_workspace.save()

        async_task("user_workspaces_server.tasks.delete_workspace", shared_workspace.pk, cluster="long")

        return JsonResponse({"message": "Successful.", "success": True})
