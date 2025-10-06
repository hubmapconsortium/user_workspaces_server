import logging
from abc import ABC, abstractmethod

import requests as http_r
from django.contrib.auth.models import User

from user_workspaces_server import models

logger = logging.getLogger(__name__)


class AbstractUserAuthentication(ABC):
    def __init__(self, config):
        self.connection_details = config.get("connection_details", {})

    @abstractmethod
    def has_permission(self, internal_user):
        pass

    @abstractmethod
    def api_authenticate(self, request):
        pass

    def create_internal_user(self, user_info):
        if "username" not in user_info:
            return False

        # TODO: Consider creating the root dir for the user at this time?

        return User.objects.create_user(
            user_info["username"],
            email=user_info.get("email", None),
            **{
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
            },
        )

    @abstractmethod
    def create_external_user(self, external_user_to_create):
        pass

    def create_external_user_mapping(self, user_mapping_to_create):
        external_user_to_create = models.ExternalUserMapping(**user_mapping_to_create)
        external_user_to_create.save()

        return external_user_to_create

    def get_internal_user(self, user_info):
        try:
            return User.objects.filter(**user_info).first()
        except User.DoesNotExist:
            logger.exception(f"Unable to find user {user_info}")
            return False

    @abstractmethod
    def get_external_user(self, external_user_id):
        pass

    def get_external_user_mapping(self, user_info):
        try:
            return models.ExternalUserMapping.objects.filter(**user_info).first()
        except models.ExternalUserMapping.DoesNotExist:
            logger.exception(f"Unable to find external user mapping {user_info}")
            return False

    @abstractmethod
    def delete_external_user(self, user_id):
        pass

    def health_check(self):
        connected = True
        try:
            response = http_r.get(self.connection_details.get("health_check_url")).json()
            message = response.json()
        except Exception as e:
            logger.info(f"Issue with health check {repr(e)}")
            connected = False
            message = repr(e)

        return {"status": connected, "message": message}
