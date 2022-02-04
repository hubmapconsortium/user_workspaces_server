from django.http import JsonResponse
from django.views import View
from django.contrib.auth.models import User
import user_workspaces_server.controllers.job_types.local_test_job
from . import models
from django.apps import apps
import json
from datetime import datetime
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ParseError
import os
from django_q.tasks import async_task


class UserWorkspacesServerTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        # grab the main auth method, just force globus auth for now

        api_user_authentication = apps.get_app_config('user_workspaces_server').api_user_authentication

        # hit the api_authenticate method
        api_user = api_user_authentication.api_authenticate(request)

        if type(api_user) == User:
            token, created = Token.objects.get_or_create(user=api_user)
            result = Response({'token': token.key})
        elif type(api_user) == Response:
            result = api_user
        else:
            raise AuthenticationFailed

        return result


class WorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id=None):
        workspace = models.Workspace.objects.filter(id=workspace_id, user_id=request.user).first()

        # TODO: Add url parameter searching functionality

        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'workspace': workspace}})

    def post(self, request):
        body = json.loads(request.body)

        workspace_data = {
            "user_id": request.user,
            "name": body['name'],
            "description": body['description'],
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": body['workspace_details']
        }

        main_storage = apps.get_app_config('user_workspaces_server').main_storage
        external_user_mapping = main_storage.storage_user_authentication.has_permission(request.user)

        if not external_user_mapping:
            return JsonResponse(
                {
                    'message': 'User could not be found/created on main storage system.',
                    'success': False
                },
                status=500
            )

        workspace = models.Workspace(**workspace_data)
        workspace.save()

        # file_path should be relative, not absolute
        workspace.file_path = os.path.join(request.user.username, str(workspace.pk))

        main_storage.create_dir(workspace.file_path)
        main_storage.set_ownership(workspace.file_path, external_user_mapping)

        workspace.save()

        return JsonResponse({'message': 'Successful!', 'success': True})

    def put(self, request, workspace_id, put_type):
        if put_type.lower() == 'start':
            body = json.loads(request.body)
            if 'job_type' not in body or 'job_details' not in body:
                raise ParseError('Missing job_type or job_details')

            try:
                workspace = models.Workspace.objects.get(id=workspace_id, user_id=request.user)
            except models.Workspace.DoesNotExist:
                raise PermissionDenied('Workspace does not exist/is not owned by this user.')

            resource = apps.get_app_config('user_workspaces_server').available_resources['local_resource']

            # I think that instantiating the job here and passing that through to the resource makes the most sense

            # TODO: Grab the correct job type based on the request
            job_to_launch = user_workspaces_server.controllers.job_types.local_test_job.LocalTestJob()

            resource_job_id = resource.launch_job(job_to_launch, workspace)

            job_data = {
                "workspace_id": workspace,
                "job_type": body['job_type'],
                "datetime_created": datetime.now(),
                "job_details": {
                    'request_job_details': body['job_details']
                },
                "resource_job_id": resource_job_id,
                "resource_name": type(resource).__name__,
                "status": "Pending"
            }

            job = models.Job(**job_data)
            job.save()

            # This function should also spin up a loop for the job to be updated.
            async_task('user_workspaces_server.tasks.update_job_status', job.pk,
                       hook='user_workspaces_server.tasks.queue_job_update')

            return JsonResponse({'message': 'Successful start!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobView(View):
    def get(self, request, job_id=None):
        job = models.Job.objects.filter(id=job_id, user_id=request.user).first()

        # TODO: Add url parameter searching functionality

        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'job': job}})

    def put(self, request, job_id, put_type):
        if put_type.lower() == 'stop':
            job = models.Job.objects.filter(id=job_id, user_id=request.user).first()

            return JsonResponse({'message': 'Successful stop!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobTypeView(View):
    def get(self, request):
        # TODO: Grab job types from the config.
        job_types = {}
        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'job_types': job_types}})
