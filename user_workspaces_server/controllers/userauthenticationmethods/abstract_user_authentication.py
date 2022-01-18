from abc import ABC, abstractmethod
from user_workspaces_server import models
from django.contrib.auth.models import User


class AbstractUserAuthentication(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def has_permission(self, internal_user):
        pass

    @abstractmethod
    def api_authenticate(self, request):
        pass

    def create_internal_user(self, user_info):
        if 'username' not in user_info:
            return False

        # TODO: Consider creating the root dir for the user at this time?

        return User.objects.create_user(
            user_info['username'],
            email=user_info.get('email', None)
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
        except Exception as e:
            print(e)
            return False

    @abstractmethod
    def get_external_user(self, external_user_id):
        pass

    def get_external_user_mapping(self, user_info):
        try:
            return models.ExternalUserMapping.objects.filter(**user_info).first()
        except Exception as e:
            print(e)
            return False

    @abstractmethod
    def delete_external_user(self, user_id):
        pass
