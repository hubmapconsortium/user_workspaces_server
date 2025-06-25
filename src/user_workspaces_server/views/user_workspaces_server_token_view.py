import logging

from django.apps import apps
from django.contrib.auth.models import User
from django.http import JsonResponse
from django_q.tasks import async_task
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class UserWorkspacesServerTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        api_user_authentication = apps.get_app_config(
            "user_workspaces_server"
        ).api_user_authentication

        # hit the api_authenticate method
        api_user = api_user_authentication.api_authenticate(request)

        if isinstance(api_user, User):
            token, created = Token.objects.get_or_create(user=api_user)
            result = JsonResponse(
                {
                    "success": True,
                    "message": "Successful authentication.",
                    "token": token.key,
                }
            )

            async_task(
                "user_workspaces_server.tasks.check_main_storage_user", api_user, cluster="long"
            )
        elif isinstance(api_user, Response):
            result = api_user
        else:
            raise AuthenticationFailed

        return result
