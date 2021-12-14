from abc import ABC, abstractmethod


class AbstractJob(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def status_check(self):
        pass
