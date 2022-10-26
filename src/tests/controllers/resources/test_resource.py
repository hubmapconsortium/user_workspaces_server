import logging

from user_workspaces_server.controllers.resources.abstract_resource import (
    AbstractResource,
)
from user_workspaces_server.models import Job

logger = logging.getLogger(__name__)


class TestResource(AbstractResource):
    def translate_status(self, status):
        status_list = {
            "sleeping": Job.Status.RUNNING,
            "running": Job.Status.RUNNING,
            "zombie": Job.Status.COMPLETE,
            "complete": Job.Status.COMPLETE,
            "dead": Job.Status.FAILED,
        }

        return status_list[status]

    def launch_job(self, job, workspace):
        return 0

    def get_resource_job(self, job):
        return {"status": Job.Status.COMPLETE}

    def get_job_core_hours(self, job):
        return 0

    def stop_job(self, job):
        return True
