from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
import user_workspaces_server.controllers.job_types.jupyter_lab_job
from . import models
from user_workspaces_server.exceptions import WorkspaceClientException
from django.conf import settings
from django.apps import apps
from pathlib import Path
from django.forms.models import model_to_dict
import json
from datetime import datetime
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import (
    AuthenticationFailed,
    ParseError,
    NotFound,
    APIException,
)
import os
from django_q.tasks import async_task
import requests as http_r
import logging

logger = logging.getLogger(__name__)


# TODO: Add more robust query param support. Filter types, filtering by date.
class UserWorkspacesServerTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        api_user_authentication = apps.get_app_config(
            "user_workspaces_server"
        ).api_user_authentication

        # hit the api_authenticate method
        api_user = api_user_authentication.api_authenticate(request)

        if type(api_user) == User:
            token, created = Token.objects.get_or_create(user=api_user)
            result = JsonResponse(
                {
                    "success": True,
                    "message": "Successful authentication.",
                    "token": token.key,
                }
            )
        elif type(api_user) == Response:
            result = api_user
        else:
            raise AuthenticationFailed

        return result


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

        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {"workspaces": workspaces},
            }
        )

    def post(self, request):
        try:
            body = json.loads(request.body)
        except Exception as e:
            raise ParseError(f"Invalid JSON: {str(e)}")

        if "name" not in body or "description" not in body:
            raise ParseError("Missing required fields.")

        workspace_details = body.get("workspace_details", {})

        if type(workspace_details) != dict:
            raise ParseError("Workspace details not JSON.")

        workspace_data = {
            "user_id": request.user,
            "name": body["name"],
            "description": body["description"],
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": {
                "request_workspace_details": workspace_details,
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
            main_storage.set_ownership(
                workspace.file_path, external_user_mapping, recursive=True
            )

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
                    "workspace": model_to_dict(
                        workspace, models.Workspace.get_dict_fields()
                    )
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
            workspace = models.Workspace.objects.get(
                id=workspace_id, user_id=request.user
            )
        except models.Workspace.DoesNotExist:
            raise NotFound(f"Workspace {workspace_id} not found for user.")

        if not put_type:
            try:
                body = json.loads(request.body)
            except Exception as e:
                raise ParseError(f"Invalid JSON: {str(e)}")

            workspace.name = body.get("name", workspace.name)
            workspace.description = body.get("description", workspace.description)

            workspace.save()

            workspace_details = body.get("workspace_details", {})

            if type(workspace_details) != dict:
                raise ParseError("Workspace details not JSON.")

            try:
                main_storage.create_symlinks(workspace, workspace_details)
                main_storage.create_files(workspace, workspace_details)
                main_storage.set_ownership(
                    workspace.file_path, external_user_mapping, recursive=True
                )
            except Exception:
                logger.exception(
                    "Failure when creating symlink/files or setting ownership."
                )
                raise

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

            if type(job_details) != dict:
                raise ParseError("Job details not JSON.")

            # TODO: Grabbing the resource needs to be a bit more intelligent
            resource = apps.get_app_config("user_workspaces_server").main_resource

            # TODO: Check whether user has permission for this resource (and resource storage).

            job_data = {
                "workspace_id": workspace,
                "job_type": body["job_type"],
                "datetime_created": datetime.now(),
                "job_details": {
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
            # TODO: Grab the correct job type based on the request
            job_to_launch = user_workspaces_server.controllers.job_types.jupyter_lab_job.JupyterLabJob(
                settings.UWS_CONFIG["available_job_types"]["jupyter_lab"][
                    "environment_details"
                ][settings.UWS_CONFIG["main_resource"]],
                model_to_dict(job),
            )

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

            main_storage.set_ownership(
                workspace.file_path, external_user_mapping, recursive=True
            )

            async_task("user_workspaces_server.tasks.update_workspace", workspace.pk)

            return JsonResponse({"message": "Successful upload.", "success": True})
        else:
            raise WorkspaceClientException("Invalid PUT type passed.")

    def delete(self, request, workspace_id):
        try:
            workspace = models.Workspace.objects.get(
                user_id=request.user, id=workspace_id
            )
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
            logger.error(
                f"Workspace {workspace_id} deletion failed due to invalid path"
            )
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

        return JsonResponse(
            {"message": "Successful.", "success": True, "data": {"jobs": job}}
        )

    def put(self, request, job_id, put_type):
        try:
            job = models.Job.objects.get(workspace_id__user_id=request.user, id=job_id)
        except models.Job.DoesNotExist:
            raise NotFound(f"Job {job_id} not found for user.")

        if put_type.lower() == "stop":
            if job.resource_job_id == -1:
                job.status = job.Status.COMPLETE
                job.save()
                return JsonResponse({"message": "Successful stop.", "success": True})

            resource = apps.get_app_config("user_workspaces_server").main_resource

            # This needs to be done asynchronously.
            if resource.stop_job(job):
                return JsonResponse({"message": "Successful stop.", "success": True})
            else:
                raise WorkspaceClientException("Failed to stop job.")
        else:
            raise WorkspaceClientException("Invalid PUT type passed.")


class JobTypeView(APIView):
    def get(self, request):
        # TODO: Grab job types from the config.
        job_types = {}
        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {"job_types": job_types},
            }
        )


class PassthroughView(APIView):
    permission_classes = []

    def get(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.get(url, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough GET failure")
            raise APIException

    def post(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.post(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough POST failure")
            raise APIException

    def patch(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.patch(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough PATCH failure")
            raise APIException

    def put(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.put(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough PUT failure")
            raise APIException

    def delete(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.delete(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough DELETE failure")
            raise APIException


class StatusView(APIView):
    permission_classes = []

    def get(self, request):
        base_dir = Path(__file__).resolve().parent.parent
        version_file_path = os.path.join(base_dir, "VERSION")
        build_file_path = os.path.join(base_dir, "BUILD")

        version = (
            open(version_file_path).read().strip()
            if os.path.exists(version_file_path)
            else "invalid_version"
        )
        build = (
            open(build_file_path).read().strip()
            if os.path.exists(build_file_path)
            else "invalid_build"
        )

        response_data = {
            "message": "",
            "success": True,
            "version": version,
            "build": build,
        }

        return JsonResponse(response_data)
