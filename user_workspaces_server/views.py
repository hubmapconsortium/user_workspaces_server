from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.models import User
from . import models
from .controllers.userauthenticationmethods import globus_user_authentication
import json
from datetime import datetime
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed


class UserWorkspacesServerTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        # grab the main auth method, just force globus auth for now
        user_auth = globus_user_authentication.GlobusUserAuthentication(
            settings.CONFIG['available_user_authentication'][settings.CONFIG['api_user_authentication']]
            ['connection_details']
        )

        # hit the api_authenticate method
        api_user = user_auth.api_authenticate(request)

        if type(api_user) == User:
            token, created = Token.objects.get_or_create(user=api_user)
            result = Response({'token': token.key})
        elif type(api_user) == Response:
            result = api_user
        else:
            raise AuthenticationFailed

        return result


class WorkspaceView(View):
    def get(self, request, workspace_id=None):
        workspace = models.Workspace.objects.filter(id=workspace_id).first()

        # TODO: Add url parameter searching functionality

        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'workspace': workspace}})

    def post(self, request):
        body = json.loads(request.body)

        workspace_data = {
            "name": body['name'],
            "description": body['description'],
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": body['workspace_details']
        }

        # Have to define file_path still

        workspace = models.Workspace(**workspace_data)
        workspace.save()

        return JsonResponse({'message': 'Successful!', 'success': True})

    def put(self, request, workspace_id, put_type):
        if put_type.lower() == 'start':
            body = json.loads(request.body)
            workspace = models.Workspace.objects.filter(id=workspace_id).first()
            job_data = {
                "workspace_id": workspace,
                "job_type": body['job_type'],
                "datetime_created": datetime.now(),
                "job_details": body['job_details']
            }

            # TODO: Once we have JobType defined, we need to do it like this
            # job = models.JobType(**job_data)

            job = models.Job(**job_data)
            job.save()

            return JsonResponse({'message': 'Successful start!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobView(View):
    def get(self, request, job_id=None):
        job = models.Job.objects.filter(id=job_id).first()

        # TODO: Add url parameter searching functionality

        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'job': job}})

    def put(self, request, job_id, put_type):
        if put_type.lower() == 'stop':
            job = models.Job.objects.filter(id=job_id).first()

            # job.stop()

            return JsonResponse({'message': 'Successful stop!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobTypeView(View):
    def get(self, request):
        # TODO: Grab job types from the config.
        job_types = {}
        return JsonResponse({'message': 'Successful!', 'success': True, 'data': {'job_types': job_types}})
