import logging

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from user_workspaces_server.apps import UserWorkspacesServerConfig

logger = logging.getLogger(__name__)

config = UserWorkspacesServerConfig

class UserWorkspacesServerTokenView(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        api_user_authentication = config.api_user_authentication

        # hit the api_authenticate method
        api_user = api_user_authentication.api_authenticate(request)

        if isinstance(api_user, User):
            token, _ = Token.objects.get_or_create(user=api_user)
            result = Response(
                {
                    "success": True,
                    "message": "Successful authentication.",
                    "token": token.key,
                }
            )
        elif isinstance(api_user, Response):
            result = api_user
        else:
            raise AuthenticationFailed

        return result
