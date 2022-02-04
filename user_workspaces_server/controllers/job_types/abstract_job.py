from abc import ABC, abstractmethod


class AbstractJob(ABC):
    @abstractmethod
    def get_script(self):
        pass

    @abstractmethod
    def status_check(self):
        # Should return job_details information
        pass
