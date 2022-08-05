from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token


class UserWorkspacesTokenAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_UWS_AUTHORIZATION')

        if auth_header is None:
            return None

        identifier, token = auth_header.split(' ')

        try:
            valid_token = Token.objects.get(key=token)
        except Exception as e:
            raise AuthenticationFailed('Invalid token provided.')

        return valid_token.user, None
