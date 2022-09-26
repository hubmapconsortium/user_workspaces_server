import logging

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class UserWorkspacesTokenAuthentication(authentication.TokenAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_UWS_AUTHORIZATION')

        if auth_header is None:
            return None

        try:
            identifier, token = auth_header.split(' ')
        except ValueError:
            logger.exception(f'Invalid auth header format: {auth_header}')
            raise AuthenticationFailed('Invalid auth header format.')

        try:
            valid_token = Token.objects.get(key=token)
        except Token.DoesNotExist:
            logger.exception(f'Token {token} not found.')
            raise AuthenticationFailed('Invalid token provided.')

        return valid_token.user, None
