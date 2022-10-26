from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import (
    AbstractUserAuthentication,
)
import json
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.authtoken.models import Token


class TestUserAuthentication(AbstractUserAuthentication):
    def has_permission(self, internal_user):
        external_user_mapping = self.get_external_user_mapping(
            {"user_id": internal_user, "user_authentication_name": type(self).__name__}
        )

        if not external_user_mapping:
            # If the mapping does not exist, we have to try to "find" an external user
            # based on the info we have from the internal user
            external_user_mapping = self.create_external_user_mapping(
                {
                    "user_id": internal_user,
                    "user_authentication_name": type(self).__name__,
                    "external_user_id": "test",
                    "external_username": "test",
                    "external_user_details": {},
                }
            )
            # If the mapping does exist, we just get that external user, to confirm it exists
            return external_user_mapping
        else:
            return external_user_mapping

    def api_authenticate(self, request):
        try:
            body = json.loads(request.body)
        except Exception as e:
            raise ParseError(repr(e))

        if "client_token" not in body:
            raise ParseError(
                "Missing client_token. Please have admin generate a token for you."
            )

        if "user_info" not in body:
            raise ParseError(
                "Missing user_info. Please provide user_info to get user_token."
            )

        try:
            client_token = body["client_token"]
            token = Token.objects.get(key=client_token)
            token_user = token.user

            if not token_user.groups.filter(name="api_clients").exists():
                raise PermissionDenied(
                    "Token is invalid for api_authentication. "
                    "Please contact administrator to generate valid token."
                )

            # Let's require username and email here
            user_info = body["user_info"]

            if "username" not in user_info or "email" not in user_info:
                raise ParseError("Missing username or email in user_info.")

            external_user_mapping = self.get_external_user_mapping(
                {
                    "user_authentication_name": type(self).__name__,
                    "external_username": user_info["username"],
                }
            )

            if not external_user_mapping:
                internal_user = self.get_internal_user(
                    {"username": user_info["username"], "email": user_info["email"]}
                )

                if not internal_user:
                    internal_user = self.create_internal_user(
                        {"username": user_info["username"], "email": user_info["email"]}
                    )

                return internal_user
            else:
                return external_user_mapping.user_id

        except Exception as e:
            return e

    def create_external_user(self, user_info):
        return {
            "external_username": "test",
            "external_user_id": "test",
            "external_user_uid": "test",
            "external_user_gid": "test",
            "external_user_details": {},
        }

    def get_external_user(self, external_user_info):
        return {
            "external_username": "test",
            "external_user_id": "test",
            "external_user_uid": "test",
            "external_user_gid": "test",
            "external_user_details": {},
        }

    def delete_external_user(self, user_id):
        pass
