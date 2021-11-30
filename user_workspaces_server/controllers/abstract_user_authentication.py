from abc import ABC, abstractmethod


class AbstractUserAuthentication(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def create(self, user_to_create):
        pass

    @abstractmethod
    def exists(self, user_id):
        pass

    @abstractmethod
    def delete(self, user_id):
        pass
