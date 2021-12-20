from abc import ABC, abstractmethod


class AbstractUserAuthentication(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def api_authenticate(self, request):
        pass

    @abstractmethod
    def create_internal_user(self, internal_user_to_create):
        pass

    @abstractmethod
    def create_external_user(self, external_user_to_create):
        pass

    @abstractmethod
    def create_external_user_mapping(self, user_mapping_to_create):
        pass

    @abstractmethod
    def internal_user_exists(self, user_id):
        pass

    @abstractmethod
    def external_user_exists(self, user_id):
        pass

    @abstractmethod
    def delete_external_user(self, user_id):
        pass
