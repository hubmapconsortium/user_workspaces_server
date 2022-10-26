from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import (
    AbstractUserAuthentication,
)
import pwd
import subprocess
import json
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.authtoken.models import Token
import logging

logger = logging.getLogger(__name__)


class LocalUserAuthentication(AbstractUserAuthentication):
    def __init__(self, config):
        super().__init__(config)
        self.create_external_users = self.connection_details.get(
            "create_external_users", False
        )
        self.operating_system = self.connection_details.get("operating_system", "").lower()

    def has_permission(self, internal_user):
        external_user_mapping = self.get_external_user_mapping(
            {"user_id": internal_user, "user_authentication_name": type(self).__name__}
        )

        if not external_user_mapping:
            # If the mapping does not exist, we have to try to "find" an external user
            # based on the info we have from the internal user
            external_user = self.get_external_user({"username": internal_user.username})

            if not external_user:
                # No user found, return false
                if self.create_external_users:
                    external_user = self.create_external_user(
                        {"username": internal_user.username}
                    )
                    if not external_user:
                        return False
                else:
                    return False

            # User found, create mapping
            external_user_mapping = self.create_external_user_mapping(
                {
                    "user_id": internal_user,
                    "user_authentication_name": type(self).__name__,
                    "external_user_id": external_user["external_user_uid"],
                    "external_username": external_user["external_username"],
                    "external_user_details": external_user["external_user_details"],
                }
            )
            # If the mapping does exist, we just get that external user, to confirm it exists
            return (
                external_user_mapping
                if self.get_external_user(
                    {"external_user_id": external_user_mapping.external_user_id}
                )
                else False
            )
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
            logger.error(repr(e))
            return e

    def create_external_user(self, user_info):
        if self.operating_system == "linux":
            output = subprocess.run(
                ["useradd", user_info["username"]], capture_output=True
            )
            if output.returncode == 0:
                external_user = pwd.getpwnam(user_info["username"])
            else:
                # TODO: Add logging here
                external_user = False
        elif self.operating_system == "osx":
            external_user = False
        else:
            external_user = False
        # Need to return username and id
        return (
            {
                "external_username": external_user[0],
                "external_user_id": external_user[2],
                "external_user_uid": external_user[2],
                "external_user_gid": external_user[3],
                "external_user_details": external_user,
            }
            if external_user
            else external_user
        )

    def get_external_user(self, external_user_info):
        try:
            if "username" in external_user_info:
                external_user = pwd.getpwnam(external_user_info["username"])
            elif "external_user_id" in external_user_info:
                external_user = pwd.getpwuid(
                    int(external_user_info["external_user_id"])
                )
            else:
                external_user = False
            return (
                {
                    "external_username": external_user[0],
                    "external_user_id": external_user[2],
                    "external_user_uid": external_user[2],
                    "external_user_gid": external_user[3],
                    "external_user_details": external_user,
                }
                if external_user
                else external_user
            )
        except Exception as e:
            logger.error(repr(e))
            return False

    def delete_external_user(self, user_id):
        pass
