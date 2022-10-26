import logging
import os
import signal
import subprocess
import time

import psutil
from django.core.files.base import ContentFile

from user_workspaces_server.controllers.resources.abstract_resource import \
    AbstractResource
from user_workspaces_server.models import Job

logger = logging.getLogger(__name__)


class LocalResource(AbstractResource):
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
        workspace_full_path = os.path.join(
            self.resource_storage.root_dir, workspace.file_path
        )
        job_full_path = os.path.join(workspace_full_path, f'.{job.job_details["id"]}')
        script_name = f"{str(time.time())}.sh"
        script_path = os.path.join(job_full_path, script_name)
        # Get the script content

        self.resource_storage.create_file(
            job_full_path,
            ContentFile(
                bytes(
                    job.get_script({"workspace_full_path": workspace_full_path}),
                    "utf-8",
                ),
                name=script_name,
            ),
        )

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.set_ownership(job_full_path, user_info)
        self.resource_storage.set_ownership(script_path, user_info)

        os.chmod(script_path, 0o744)

        process = subprocess.Popen(
            ["sudo", "su", user_info.external_username, "-s", "/bin/bash", script_path],
            stdin=None,
            stdout=None,
            stderr=None,
            cwd=job_full_path,
        )
        return process.pid

    def get_resource_job(self, job):
        resource_job_id = job.resource_job_id
        try:
            resource_job = psutil.Process(resource_job_id).as_dict()
            resource_job["status"] = self.translate_status(resource_job["status"])
            return resource_job
        except Exception as e:
            logger.exception(repr(e))
            return {"status": "complete"}

    def get_job_core_hours(self, job):
        datetime_running = job.datetime_end - job.datetime_start
        return (
            datetime_running.total_seconds() / 3600
            if datetime_running.total_seconds() != 0
            else 0
        )

    def stop_job(self, job):
        resource_job_id = job.resource_job_id
        try:
            resource_job = psutil.Process(resource_job_id)
            for child in resource_job.children(recursive=True):
                child.send_signal(signal.SIGKILL)

            resource_job.send_signal(signal.SIGKILL)
            return True
        except Exception as e:
            logger.error(repr(e))
            return False
