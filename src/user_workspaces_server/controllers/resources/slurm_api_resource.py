# THIS RESOURCE IS MEANT TO SUPPORT v0.0.40 OF THE SLURM RESPONSE SCHEMAS
import logging
import os
import time

import jwt
import requests as http_r
from rest_framework.exceptions import APIException

from user_workspaces_server.controllers.resources.abstract_resource import (
    AbstractResource,
)
from user_workspaces_server.models import Job

logger = logging.getLogger(__name__)


class SlurmAPIResource(AbstractResource):

    def translate_status(self, status):
        status_list = {
            "PENDING": Job.Status.PENDING,
            "RUNNING": Job.Status.RUNNING,
            "SUSPENDED": Job.Status.PENDING,
            "COMPLETING": Job.Status.RUNNING,
            "COMPLETED": Job.Status.COMPLETE,
            "FAILED": Job.Status.FAILED,
            "CANCELLED": Job.Status.COMPLETE,
            "TIMEOUT": Job.Status.COMPLETE,
        }

        return status_list[status]

    def launch_job(self, job, workspace, resource_options):
        # Need to generate a SLURM token (as a user) to launch a job
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        job_full_path = os.path.join(workspace_full_path, f'.{job.job_details["id"]}')

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.create_dir(job_full_path)
        self.resource_storage.set_ownership(job_full_path, user_info)

        token = self.get_user_token(user_info)

        # For pure testing, lets just set a var in the connection details.
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
                "nodes": 1,
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

        if len(slurm_response["errors"]):
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
            if len(resource_job["errors"]):
                raise APIException(resource_job["errors"])
            resource_job = resource_job["jobs"][0]

            resource_job_state = resource_job.get("job_state", [])[0]
            if resource_job_state == "TIMEOUT":
                logger.error(
                    f"Workspaces Job {job.id}/Slurm job {job.resource_job_id} has timed out."
                )

            resource_job["status"] = self.translate_status(resource_job_state)
            end_time = resource_job.get("end_time", {}).get("number")
            if end_time is not None:
                time_left = max(0, end_time - time.time())
            else:
                time_left = None  # or some other value that indicates unknown

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
            if len(resource_job["errors"]):
                raise APIException(resource_job["errors"])

            resource_job = resource_job["jobs"][0]
            end_time = resource_job.get("end_time", {}).get("number", 0)
            start_time = resource_job.get("start_time", {}).get("number", 0)
            time_running = end_time - start_time
            num_cores = resource_job.get("job_resources", {}).get("allocated_cpus", 0)
            core_seconds = time_running * num_cores

            # We use (end time - start time) * allocated cores which is the same as the wall time * cores.
            return core_seconds / 3600 if core_seconds != 0 else 0
        except Exception as e:
            logger.error(repr(e))
            return 0

    def stop_job(self, job):
        user_info = self.resource_user_authentication.has_permission(job.workspace_id.user_id)

        token = self.get_user_token(user_info)

        # For pure testing, lets just set a var in the connection details.
        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-Token": token,
            "Slurm-User": user_info.external_username,
        }

        try:
            resource_job = http_r.delete(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers,
            ).json()
            if len(resource_job["errors"]):
                raise APIException(resource_job["errors"])

            return True
        except Exception as e:
            logger.error((repr(e)))
            return False

    def get_user_token_from_slurm(self, external_user):
        headers = {
            "Authorization": f'Token {self.connection_details.get("api_token")}',
            "Slurm-User": external_user.external_username,
            "Slurm-Lifespan": self.connection_details.get("token_lifespan"),
        }
        response = http_r.get(
            f'{self.connection_details.get("root_url")}/getSlurmToken/', headers=headers
        )

        if response.status_code not in [200, 201]:
            raise APIException(response.text)

        return response.json()["slurm_token"]

    def get_user_token(self, external_user):
        external_user_mapping = self.resource_user_authentication.get_external_user_mapping(
            {
                "user_id": external_user.user_id,
                "user_authentication_name": f"{type(self).__name__}Authentication",
            }
        )

        if not external_user_mapping:
            token = self.get_user_token_from_slurm(external_user)
            external_user_mapping = self.resource_user_authentication.create_external_user_mapping(
                {
                    "user_id": external_user.user_id,
                    "user_authentication_name": f"{type(self).__name__}Authentication",
                    "external_user_id": external_user.user_id,
                    "external_username": external_user.external_username,
                    "external_user_details": {"token": token},
                }
            )
        else:
            decoded_token = jwt.decode(
                external_user_mapping.external_user_details["token"],
                options={"verify_signature": False},
            )
            if time.time() > decoded_token["exp"]:
                # Update token
                external_user_mapping.external_user_details["token"] = (
                    self.get_user_token_from_slurm(external_user)
                )
                external_user_mapping.save()

        return external_user_mapping.external_user_details["token"]

    def translate_options(self, resource_options):
        # Should translate the options into a format that can be used by the resource
        translated_options = super().translate_options(resource_options)
        gpu_enabled = resource_options.get("gpu_enabled", False)
        if isinstance(gpu_enabled, bool) and gpu_enabled:
            translated_options["tres_per_job"] = "gres/gpu=1"
            if gpu_partition := self.config.get("gpu_partition"):
                translated_options["partition"] = gpu_partition
        return translated_options
