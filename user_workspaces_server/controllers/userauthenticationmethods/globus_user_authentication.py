from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import \
    AbstractUserAuthentication
from user_workspaces_server import models
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from django.contrib.auth.models import User
import globus_sdk
import json
from hubmap_commons.hm_auth import AuthHelper


class GlobusUserAuthentication(AbstractUserAuthentication):
    def __init__(self, config):
        client_id = config['client_id']
        client_secret = config['client_secret']
        self.oauth = globus_sdk.ConfidentialAppAuthClient(
            client_id, client_secret)
        if not AuthHelper.isInitialized():
            self.auth_helper = AuthHelper.create(clientId=client_id, clientSecret=client_secret)
        else:
            self.auth_helper = AuthHelper.instance()

    def api_authenticate(self, request):
        body = json.loads(request.body)

        if 'redirect_url' not in body:
            raise APIException('Missing redirect url.')

        redirect_url = body['redirect_url']
        self.oauth.oauth2_start_flow(redirect_url)

        try:
            if 'code' not in body:
                auth_uri = self.oauth.oauth2_get_authorize_url(query_params={
                    "scope": "openid profile email urn:globus:auth:scope:transfer.api.globus.org:all "
                             "urn:globus:auth:scope:auth.globus.org:view_identities "
                             "urn:globus:auth:scope:groups.api.globus.org:all"
                })
                return Response({'auth_uri': auth_uri})
            else:
                code = body['code']
                tokens = self.oauth.oauth2_exchange_code_for_tokens(code)

                # Need to add call here to grab user profile info
                user_info = self.introspect_globus_user(
                    tokens.by_resource_server['groups.api.globus.org']['access_token'])

                external_user = models.ExternalUserMapping.objects.filter(
                    external_user_id=user_info['sub'], user_authentication_name=type(self).__name__
                ).first()

                return self.create_external_user_mapping(user_info).user_id \
                    if not external_user else external_user.user_id
        except Exception as e:
            return e

    def create_internal_user(self, user_info):
        return User.objects.create_user(user_info['name'], user_info['email'])

    def create_external_user(self, user_info):
        # Globus users cannot be created via their API
        pass

    def create_external_user_mapping(self, user_info):
        internal_user = User.objects.filter(username=user_info['name'], email=user_info['email']).first()
        if not internal_user:
            internal_user = self.create_internal_user(user_info)

        external_user_mapping = {
            'user_id': internal_user,
            'user_authentication_name': type(self).__name__,
            'external_user_id': user_info['sub'],
            'external_username': user_info['name']
        }

        external_user_to_create = models.ExternalUserMapping(**external_user_mapping)
        external_user_to_create.save()

        return external_user_to_create

    def internal_user_exists(self, user_id):
        return models.ExternalUserMapping.objects.filter(
            user_id=user_id, user_authentication_name=type(self).__name__
        ).exists()

    def external_user_exists(self, user_id):
        try:
            self.oauth.get_identities(ids=user_id)
        except Exception as e:
            print(e)
            return False

    def delete_external_user(self, user_id):
        # Globus users cannot be created via their API
        pass

    def introspect_globus_user(self, token):
        return self.auth_helper.getUserInfo(token, True)
