from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import \
    AbstractUserAuthentication
from rest_framework.response import Response
from flask.wrappers import Response as flask_response
from rest_framework.exceptions import ParseError
import globus_sdk
import json
from hubmap_commons.hm_auth import AuthHelper


class GlobusUserAuthentication(AbstractUserAuthentication):
    def __init__(self, config):
        client_id = config['client_id']
        client_secret = config['client_secret']
        self.authentication_type = config['authentication_type']
        self.oauth = globus_sdk.ConfidentialAppAuthClient(
            client_id, client_secret)
        if not AuthHelper.isInitialized():
            self.auth_helper = AuthHelper.create(clientId=client_id, clientSecret=client_secret)
        else:
            self.auth_helper = AuthHelper.instance()

    def has_permission(self, internal_user):
        pass

    def api_authenticate(self, request):
        body = json.loads(request.body)

        globus_user_info = self.globus_oauth_get_user_info(body) if self.authentication_type == 'oauth' \
            else (self.globus_token_get_user_info(body) if self.authentication_type == 'token' else False)

        if type(globus_user_info) in [Response, flask_response]:
            return globus_user_info

        external_user_mapping = self.get_external_user_mapping({
            'external_user_id': globus_user_info['sub'],
            'user_authentication_name': type(self).__name__
        })

        if not external_user_mapping:
            # Since its Globus, lets get the username from the email
            username = globus_user_info['email'].split('@')[0]
            internal_user = self.get_internal_user({
                'username': username,
                'email': globus_user_info['email']
            })

            if not internal_user:
                full_name = globus_user_info.get('name', []).split(' ')
                internal_user = self.create_internal_user({
                    "first_name": full_name[0],
                    "last_name": full_name[-1],
                    "username": username,
                    "email": globus_user_info['email']
                })

            globus_user_info['internal_user_id'] = internal_user
            self.create_external_user_mapping({
                'user_id': globus_user_info['internal_user_id'],
                'user_authentication_name': type(self).__name__,
                'external_user_id': globus_user_info['sub'],
                'external_username': globus_user_info['username']
            })
            return internal_user
        else:
            return external_user_mapping.user_id

    def create_external_user(self, user_info):
        # Globus users cannot be created via their API
        pass

    def get_external_user(self, external_user_info):
        try:
            self.oauth.get_identities(ids=external_user_info['external_user_id'])
            # TODO: Do additional checking here and return the User info.
        except Exception as e:
            print(e)
            return False

    def delete_external_user(self, user_id):
        # Globus users cannot be deleted via their API
        pass

    def introspect_globus_user(self, token):
        return self.auth_helper.getUserInfo(token, True)

    def globus_oauth_get_user_info(self, body):
        if 'redirect_url' not in body:
            raise ParseError('Missing redirect url.')

        redirect_url = body['redirect_url']
        self.oauth.oauth2_start_flow(redirect_url)

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
            return self.introspect_globus_user(
                tokens.by_resource_server['groups.api.globus.org']['access_token'])

    def globus_token_get_user_info(self, body):
        if 'auth_token' not in body:
            raise ParseError('Missing auth_token.')

        return self.introspect_globus_user(
            body.get('auth_token'))
