import json
import logging
import os
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django_q.tasks import async_task
from rest_framework.exceptions import APIException, NotFound, ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from user_workspaces_server import models, utils
from user_workspaces_server.exceptions import WorkspaceClientException

logger = logging.getLogger(__name__)


class WorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id=None):
        workspace = models.Workspace.objects.filter(user_id=request.user)

        if workspace_id:
            workspace = workspace.filter(id=workspace_id)
        elif params := request.GET:
            for key in set(params.keys()).intersection(
                set(models.Workspace.get_query_param_fields())
            ):
                workspace = workspace.filter(**{key: params[key]})

        workspaces = list(workspace.all().values(*models.Workspace.get_dict_fields()))

        if workspaces:
            return JsonResponse(
                {
                    "message": "Successful.",
                    "success": True,
                    "data": {"workspaces": workspaces},
                }
            )
        else:
            raise NotFound("Workspace matching given parameters could not be found.")

    def post(self, request):
        try:
            body = json.loads(request.body)
        except Exception as e:
            raise ParseError(f"Invalid JSON: {str(e)}")

        if "name" not in body or "description" not in body:
            raise ParseError("Missing required fields.")

        workspace_details = body.get("workspace_details", {})

        if not isinstance(workspace_details, dict):
            raise ParseError("Workspace details not JSON.")

        request_workspace_details = {
            "files": [{"name": file["name"]} for file in workspace_details.get("files", [])],
            "symlinks": workspace_details.get("symlinks", []),
        }

        workspace_data = {
            "user_id": request.user,
            "name": body["name"],
            "description": body["description"],
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": {
                "request_workspace_details": request_workspace_details,
                "current_workspace_details": {"files": [], "symlinks": []},
            },
            "status": "idle",
        }

        main_storage = apps.get_app_config("user_workspaces_server").main_storage
        external_user_mapping = main_storage.storage_user_authentication.has_permission(
            request.user
        )

        if not external_user_mapping:
            raise WorkspaceClientException(
                "User could not be found/created on main storage system."
            )

        workspace = models.Workspace(**workspace_data)
        workspace.save()

        # file_path should be relative, not absolute
        if external_user_mapping.external_username == "" or str(workspace.pk) == "":
            logger.error(
                f"Username {external_user_mapping.external_username} or "
                f"workspace id {str(workspace.pk)} are blank."
            )
            workspace.delete()
            return APIException(
                "Please report this error to your system administrator and try again."
            )

        workspace.file_path = os.path.join(
            external_user_mapping.external_username, str(workspace.pk)
        )

        try:
            main_storage.create_dir(workspace.file_path)

            main_storage.create_symlinks(workspace, workspace_details)
            main_storage.create_files(workspace, workspace_details)

            main_storage.set_ownership(
                external_user_mapping.external_username, external_user_mapping
            )
            main_storage.set_ownership(workspace.file_path, external_user_mapping, recursive=True)

            workspace.save()
        except Exception:
            # If there was a failure here, then we need to delete this workspace
            logger.exception("Failure when creating workspace.")
            workspace.delete()
            raise

        async_task("user_workspaces_server.tasks.update_workspace", workspace.pk)

        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {
                    "workspace": model_to_dict(workspace, models.Workspace.get_dict_fields())
                },
            }
        )

    def put(self, request, workspace_id, put_type=None):
        main_storage = apps.get_app_config("user_workspaces_server").main_storage

        external_user_mapping = main_storage.storage_user_authentication.has_permission(
            request.user
        )

        if not external_user_mapping:
            raise WorkspaceClientException(
                "User could not be found/created on main storage system."
            )

        try:
            workspace = models.Workspace.objects.get(id=workspace_id, user_id=request.user)
        except models.Workspace.DoesNotExist:
            raise NotFound(f"Workspace {workspace_id} not found for user.")

        if not put_type:
            try:
                body = json.loads(request.body)
            except Exception as e:
                raise ParseError(f"Invalid JSON: {str(e)}")

            workspace.name = body.get("name", workspace.name)
            workspace.description = body.get("description", workspace.description)

            workspace_details = body.get("workspace_details", {})

            if not isinstance(workspace_details, dict):
                raise ParseError("Workspace details not JSON.")

            try:
                main_storage.create_symlinks(workspace, workspace_details)
                main_storage.create_files(workspace, workspace_details)
                main_storage.set_ownership(
                    workspace.file_path, external_user_mapping, recursive=True
                )
            except Exception:
                logger.exception("Failure when creating symlink/files or setting ownership.")
                raise

            workspace.workspace_details["current_workspace_details"]["files"] = [
                {"name": file_name}
                for file_name in {
                    (file["name"] if file["name"][0] == "/" else f"/{file['name']}")
                    for file in workspace_details.get("files", [])
                    + workspace.workspace_details["current_workspace_details"]["files"]
                }
            ]

            workspace.workspace_details["current_workspace_details"]["symlinks"] = [
                {"name": symlink_name}
                for symlink_name in {
                    (symlink["name"] if symlink["name"][0] == "/" else f"/{symlink['name']}")
                    for symlink in workspace_details.get("symlinks", [])
                    + workspace.workspace_details["current_workspace_details"]["symlinks"]
                }
            ]

            workspace.save()

            logger.info(workspace.workspace_details)
            async_task("user_workspaces_server.tasks.update_workspace", workspace.pk)

            return JsonResponse({"message": "Update successful.", "success": True})
        if put_type.lower() == "start":
            if not main_storage.is_valid_path(workspace.file_path):
                raise APIException(
                    "Please contact a system administrator there is a failure with "
                    "the workspace directory that will not allow for jobs to be created."
                )

            try:
                body = json.loads(request.body)
            except Exception as e:
                raise ParseError(f"Invalid JSON: {str(e)}")

            if "job_type" not in body:
                raise ParseError("Missing job_type.")

            job_details = body.get("job_details", {})

            if not isinstance(job_details, dict):
                raise ParseError("Job details not JSON.")

            # TODO: Grabbing the resource needs to be a bit more intelligent
            resource = apps.get_app_config("user_workspaces_server").main_resource

            # TODO: Check whether user has permission for this resource (and resource storage).

            job_data = {
                "user_id": workspace.user_id,
                "workspace_id": workspace,
                "job_type": body["job_type"],
                "datetime_created": datetime.now(),
                "job_details": {
                    "metrics": {},
                    "request_job_details": job_details,
                    "current_job_details": {},
                },
                "resource_name": type(resource).__name__,
                "status": "pending",
                "resource_job_id": -1,
                "core_hours": 0,
            }

            job = models.Job(**job_data)
            job.save()

            # I think that instantiating the job here and passing that through to the resource makes the most sense
            try:
                job_type_config = apps.get_app_config(
                    "user_workspaces_server"
                ).available_job_types.get(body["job_type"])

                job_to_launch = utils.generate_controller_object(
                    job_type_config["job_type"],
                    "jobtypes",
                    {
                        "config": job_type_config["environment_details"][
                            settings.UWS_CONFIG["main_resource"]
                        ],
                        "job_details": model_to_dict(job),
                    },
                )
            except Exception:
                raise WorkspaceClientException("Invalid job type specified")

            resource_job_id = resource.launch_job(job_to_launch, workspace)

            job.resource_job_id = resource_job_id
            job.save()

            # This function should also spin up a loop for the job to be updated.
            async_task(
                "user_workspaces_server.tasks.update_job_status",
                job.pk,
                hook="user_workspaces_server.tasks.queue_job_update",
            )

            workspace.status = models.Workspace.Status.ACTIVE
            workspace.save()

            return JsonResponse(
                {
                    "message": "Successful start.",
                    "success": True,
                    "data": {"job": model_to_dict(job, models.Job.get_dict_fields())},
                }
            )
        elif put_type.lower() == "upload":
            if not request.FILES:
                raise WorkspaceClientException("No files found in request.")

            for file_index, file in request.FILES.items():
                main_storage.create_file(workspace.file_path, file)

            main_storage.set_ownership(workspace.file_path, external_user_mapping, recursive=True)

            async_task("user_workspaces_server.tasks.update_workspace", workspace.pk)

            return JsonResponse({"message": "Successful upload.", "success": True})
        else:
            raise WorkspaceClientException("Invalid PUT type passed.")

    def delete(self, request, workspace_id):
        try:
            workspace = models.Workspace.objects.get(user_id=request.user, id=workspace_id)
        except models.Workspace.DoesNotExist:
            raise NotFound(f"Workspace {workspace_id} not found for user.")

        if models.Job.objects.filter(
            workspace_id=workspace, status__in=["pending", "running"]
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

        if not main_storage.is_valid_path(workspace.file_path):
            logger.error(f"Workspace {workspace_id} deletion failed due to invalid path")
            workspace.status = models.Workspace.Status.ERROR
            workspace.save()
            raise APIException(
                "Please contact a system administrator there is a failure with "
                "the workspace directory that will not allow for this workspace to be deleted."
            )

        workspace.status = models.Workspace.Status.DELETING
        workspace.save()

        async_task("user_workspaces_server.tasks.delete_workspace", workspace.pk)

        return JsonResponse(
            {
                "message": f"Workspace {workspace_id} queued for deletion.",
                "success": True,
            }
        )
