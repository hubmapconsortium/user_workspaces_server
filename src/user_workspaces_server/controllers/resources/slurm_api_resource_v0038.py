# THIS RESOURCE IS MEANT TO SUPPORT v0.0.38 OF THE SLURM RESPONSE SCHEMAS
import logging
import os
import time

import requests as http_r
from rest_framework.exceptions import APIException

from user_workspaces_server.controllers.resources.slurm_api_resource import (
    SlurmAPIResource,
)
from user_workspaces_server.models import Job

logger = logging.getLogger(__name__)


class SlurmAPIResourceV0038(SlurmAPIResource):

    def launch_job(self, job, workspace, resource_options):
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        job_full_path = os.path.join(workspace_full_path, f'.{job.job_details["id"]}')

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.create_dir(job_full_path)
        self.resource_storage.set_ownership(job_full_path, user_info)

        token = self.get_user_token(user_info)

        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-Token": token,
            "Slurm-User": user_info.external_username,
        }

        time_limit = job.config.get("time_limit", "30")
        cpu_partition = self.config.get("cpu_partition", "")

        body = {
            "script": job.get_script({"workspace_full_path": workspace_full_path}),
            "job": {
                "name": f'{workspace.name} {job.job_details["id"]}',
                "current_working_directory": job_full_path,
                # v0.0.38: nodes must be an array [min_nodes, max_nodes]
                "nodes": [1],
                "standard_output": os.path.join(
                    job_full_path, f'slurm_{job.job_details["id"]}.out'
                ),
                "standard_error": os.path.join(
                    job_full_path, f'slurm_{job.job_details["id"]}_error.out'
                ),
                "environment": {
                    "SLURM_GET_USER_ENV": 1,
                    "PATH": "/bin/:/usr/bin/:/usr/local/bin/",
                    "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
                },
                "time_limit": time_limit,
                "requeue": False,
                "partition": cpu_partition,
            },
        }

        body_job_environment_copy = body["job"]["environment"].copy()

        body["job"].update(self.translate_options(resource_options))

        body["job"]["environment"].update(body_job_environment_copy)

        slurm_response = http_r.post(
            f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/',
            json=body,
            headers=headers,
        )

        if slurm_response.status_code != 200:
            raise APIException(
                slurm_response.text
                if slurm_response.text
                else "No error message returned from Slurm API, please contact "
                "system administrator for more information."
            )

        try:
            slurm_response = slurm_response.json()
        except Exception:
            logger.info(slurm_response.text)
            raise APIException(
                f"Slurm response for {job.job_details['id']} could not be deciphered: {slurm_response.text}"
            )

        if len(slurm_response.get("errors", [])):
            raise APIException(slurm_response["errors"], code=500)

        return slurm_response["job_id"]

    def get_resource_job(self, job):
        workspace = job.workspace_id
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        token = self.get_user_token(user_info)

        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-Token": token,
            "Slurm-User": user_info.external_username,
        }
        try:
            resource_job = http_r.get(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers,
            ).json()
            if len(resource_job.get("errors", [])):
                raise APIException(resource_job["errors"])
            resource_job = resource_job["jobs"][0]

            # v0.0.38: job_state is a plain string, not an array
            resource_job_state = resource_job.get("job_state", "")
            if resource_job_state == "TIMEOUT":
                logger.error(
                    f"Workspaces Job {job.id}/Slurm job {job.resource_job_id} has timed out."
                )

            resource_job["status"] = self.translate_status(resource_job_state)

            # v0.0.38: end_time is a plain integer (Unix timestamp), not an object with .number
            end_time = resource_job.get("end_time")
            if end_time is not None:
                time_left = max(0, end_time - time.time())
            else:
                time_left = None

            resource_job["current_job_details"] = {"time_left": time_left}
            return resource_job
        except Exception as e:
            logger.error(repr(e))
            return {"status": Job.Status.COMPLETE}

    def get_job_core_hours(self, job):
        workspace = job.workspace_id
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        token = self.get_user_token(user_info)

        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-Token": token,
            "Slurm-User": user_info.external_username,
        }

        try:
            resource_job = http_r.get(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers,
            ).json()
            if len(resource_job.get("errors", [])):
                raise APIException(resource_job["errors"])

            resource_job = resource_job["jobs"][0]

            # v0.0.38: start_time and end_time are plain integers (Unix timestamps)
            end_time = resource_job.get("end_time", 0)
            start_time = resource_job.get("start_time", 0)
            time_running = end_time - start_time
            num_cores = resource_job.get("job_resources", {}).get("allocated_cpus", 0)
            core_seconds = time_running * num_cores

            return core_seconds / 3600 if core_seconds != 0 else 0
        except Exception as e:
            logger.error(repr(e))
            return 0

    def stop_job(self, job):
        user_info = self.resource_user_authentication.has_permission(job.workspace_id.user_id)

        token = self.get_user_token(user_info)

        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-Token": token,
            "Slurm-User": user_info.external_username,
        }

        try:
            response = http_r.delete(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers,
            )
            # v0.0.38: DELETE response has no defined body; treat any non-error status as success
            if response.status_code not in [200, 201, 204]:
                raise APIException(f"Unexpected status {response.status_code} cancelling job {job.resource_job_id}")
            return True
        except Exception as e:
            logger.error(repr(e))
            return False

    def translate_options(self, resource_options):
        # tres_per_job is not a valid submission field in v0.0.38
        translated_options = super().translate_options(resource_options)
        translated_options.pop("tres_per_job", None)

        # GPU partition override still applies without tres_per_job
        gpu_enabled = resource_options.get("gpu_enabled", False)
        if isinstance(gpu_enabled, bool) and gpu_enabled:
            if gpu_partition := self.config.get("gpu_partition"):
                translated_options["partition"] = gpu_partition

        return translated_options
