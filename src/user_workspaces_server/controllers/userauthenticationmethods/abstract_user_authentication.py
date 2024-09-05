import logging
from abc import ABC, abstractmethod
from typing import Literal, Union

from flask.wrappers import Response as flask_response
from django.contrib.auth.models import User
from rest_framework.response import Response

from user_workspaces_server import models

logger = logging.getLogger(__name__)


class AbstractUserAuthentication(ABC):
    def __init__(self, config):
        self.connection_details = config.get("connection_details", {})

    @abstractmethod
    def has_permission(self, internal_user) -> Union[models.ExternalUserMapping, Literal[False], None]:
        pass

    @abstractmethod
    def api_authenticate(self, request) -> Union[Response, flask_response, User, models.ExternalUserMapping, Literal[False]]:
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
    def create_external_user(self, external_user_to_create) -> Union[dict, Literal[False], None]:
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
    def get_external_user(self, external_user_id) -> Union[Literal[False], dict, None]:
        pass

    def get_external_user_mapping(self, user_info) -> Union[models.ExternalUserMapping, Literal[False]]:
        external_user_mapping = models.ExternalUserMapping.objects.filter(**user_info).first()
        if not external_user_mapping:
            logger.exception(f"Unable to find external user mapping {user_info}")
            return False
        return external_user_mapping

    @abstractmethod
    def delete_external_user(self, user_id):
        pass
