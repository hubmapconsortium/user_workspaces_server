import json
import logging

import globus_sdk
from flask.wrappers import Response as flask_response
from hubmap_commons.hm_auth import AuthHelper
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.response import Response

from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import (
    AbstractUserAuthentication,
)

logger = logging.getLogger(__name__)


class GlobusUserAuthentication(AbstractUserAuthentication):
    def __init__(self, config):
        super().__init__(config)
        client_id = self.connection_details["client_id"]
        client_secret = self.connection_details["client_secret"]
        self.authentication_type = self.connection_details["authentication_type"]
        self.oauth = globus_sdk.ConfidentialAppAuthClient(client_id, client_secret)
        self.allowed_globus_groups = self.connection_details.get("allowed_globus_groups", [])
        if not AuthHelper.isInitialized():
            self.auth_helper = AuthHelper.create(clientId=client_id, clientSecret=client_secret)
        else:
            self.auth_helper = AuthHelper.instance()

    def has_permission(self, internal_user):
        """
        Verify user has permission by checking external user mapping exists
        and optionally validating Globus group membership.

        Returns:
            ExternalUserMapping on success, False on failure
        """
        external_user_mapping = self.get_external_user_mapping(
            {"user_id": internal_user, "user_authentication_name": type(self).__name__}
        )

        if not external_user_mapping:
            # No mapping exists - user needs to authenticate first
            return False

        # If group checking is enabled, validate membership
        if self.allowed_globus_groups:
            try:
                # Extract groups token from stored external_user_details
                external_user_details = external_user_mapping.external_user_details or {}
                groups_token = external_user_details.get("globus_groups_token")

                if not groups_token:
                    logger.error(
                        f"Groups token not found for user {internal_user.username}. "
                        "User may need to re-authenticate."
                    )
                    return False

                # Check if user is still a member of allowed groups
                if not self._check_group_membership(
                    groups_token, external_user_mapping.external_user_id
                ):
                    logger.warning(
                        f"User {internal_user.username} is no longer a member of allowed Globus groups."
                    )
                    return False

            except Exception as e:
                logger.error(
                    f"Error checking group membership for {internal_user.username}: {repr(e)}"
                )
                return False

        # User has valid mapping and (if required) is in allowed groups
        return external_user_mapping

    def _check_group_membership(self, groups_token, user_id):
        """
        Check if user is a member of any allowed Globus groups.

        Args:
            groups_token: Access token for Globus Groups API
            user_id: Globus user ID (sub)

        Returns:
            True if user is in at least one allowed group or if no groups configured, False otherwise
        """
        if not self.allowed_globus_groups:
            # No groups configured - skip check
            return True

        try:
            # Create GroupsClient with access token
            authorizer = globus_sdk.AccessTokenAuthorizer(groups_token)
            groups_client = globus_sdk.GroupsClient(authorizer=authorizer)

            # Get user's group memberships
            user_groups = groups_client.get_my_groups()

            # Extract group IDs from response
            user_group_ids = {group["id"] for group in user_groups}

            # Check if user is in any allowed group (OR logic)
            allowed_groups_set = set(self.allowed_globus_groups)
            intersection = user_group_ids.intersection(allowed_groups_set)

            if intersection:
                logger.info(f"User {user_id} is member of allowed groups: {intersection}")
                return True
            else:
                logger.warning(
                    f"User {user_id} is not a member of any allowed groups. "
                    f"User groups: {user_group_ids}, Allowed: {allowed_groups_set}"
                )
                return False

        except globus_sdk.GlobusAPIError as e:
            logger.error(f"Globus API error checking groups for {user_id}: {e.code} - {e.message}")
            # Fail closed - deny access on API errors
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking groups for {user_id}: {repr(e)}")
            # Fail closed - deny access on unexpected errors
            return False

    def api_authenticate(self, request):
        try:
            body = json.loads(request.body)
        except Exception as e:
            raise ParseError(repr(e))

        globus_user_info = (
            self.globus_oauth_get_user_info(body)
            if self.authentication_type == "oauth"
            else (
                self.globus_token_get_user_info(body)
                if self.authentication_type == "token"
                else False
            )
        )

        if type(globus_user_info) in [Response, flask_response]:
            return globus_user_info

        external_user_mapping = self.get_external_user_mapping(
            {
                "external_user_id": globus_user_info["sub"],
                "user_authentication_name": type(self).__name__,
            }
        )

        # Check whether the user is part of predefined set of Globus groups
        if not external_user_mapping and self.allowed_globus_groups:
            # For new users, check group membership before creating account
            groups_token = globus_user_info.get("globus_groups_token")
            if not groups_token:
                raise PermissionDenied("Groups token not available for authentication.")

            if not self._check_group_membership(groups_token, globus_user_info["sub"]):
                raise PermissionDenied(
                    "User is not a member of any allowed Globus groups. "
                    "Please contact your administrator for access."
                )

        if not external_user_mapping:
            # Since its Globus, lets get the username from the email
            username = globus_user_info["email"].split("@")[0]
            internal_user = self.get_internal_user(
                {"username": username, "email": globus_user_info["email"]}
            )

            if not internal_user:
                full_name = globus_user_info.get("name", []).split(" ")
                internal_user = self.create_internal_user(
                    {
                        "first_name": full_name[0],
                        "last_name": full_name[-1],
                        "username": username,
                        "email": globus_user_info["email"],
                    }
                )

            globus_user_info["internal_user_id"] = internal_user
            self.create_external_user_mapping(
                {
                    "user_id": globus_user_info["internal_user_id"],
                    "user_authentication_name": type(self).__name__,
                    "external_user_id": globus_user_info["sub"],
                    "external_username": globus_user_info["username"],
                    "external_user_details": globus_user_info,
                }
            )
            return internal_user
        else:
            return external_user_mapping.user_id

    def create_external_user(self, user_info):
        # Globus users cannot be created via their API
        pass

    def get_external_user(self, external_user_info):
        try:
            self.oauth.get_identities(ids=external_user_info["external_user_id"])
            # TODO: Do additional checking here and return the User info.
        except Exception as e:
            logger.error(repr(e))
            return False

    def delete_external_user(self, user_id):
        # Globus users cannot be deleted via their API
        pass

    def introspect_globus_user(self, token):
        return self.auth_helper.getUserInfo(token, True)

    def globus_oauth_get_user_info(self, body):
        if "redirect_url" not in body:
            raise ParseError("Missing redirect url.")

        redirect_url = body["redirect_url"]
        self.oauth.oauth2_start_flow(redirect_url)

        if "code" not in body:
            auth_uri = self.oauth.oauth2_get_authorize_url(
                query_params={
                    "scope": "openid profile email urn:globus:auth:scope:transfer.api.globus.org:all "
                    "urn:globus:auth:scope:auth.globus.org:view_identities "
                    "urn:globus:auth:scope:groups.api.globus.org:all"
                }
            )
            return Response({"auth_uri": auth_uri})
        else:
            code = body["code"]
            tokens = self.oauth.oauth2_exchange_code_for_tokens(code)

            # Get user profile info using groups token
            groups_token = tokens.by_resource_server["groups.api.globus.org"]["access_token"]
            user_info = self.introspect_globus_user(groups_token)

            # Store the groups token for later group membership checking
            user_info["globus_groups_token"] = groups_token

            return user_info

    def globus_token_get_user_info(self, body):
        if "auth_token" not in body:
            raise ParseError("Missing auth_token.")

        auth_token = body.get("auth_token")
        user_info = self.introspect_globus_user(auth_token)

        # Store the auth token as groups token for group membership checking
        user_info["globus_groups_token"] = auth_token

        return user_info
