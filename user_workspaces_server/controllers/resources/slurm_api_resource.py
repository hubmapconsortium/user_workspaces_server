from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import os
import requests as http_r
from rest_framework.exceptions import APIException


class SlurmAPIResource(AbstractResource):
    def __init__(self, config, resource_storage, resource_user_authentication):
        super().__init__(config, resource_storage, resource_user_authentication)
        self.connection_details = self.config.get('connection_details')

    def translate_status(self, status):
        status_list = {
            'PENDING': 'pending',
            'RUNNING': 'running',
            'SUSPENDED': 'pending',
            'COMPLETING': 'running',
            'COMPLETED': 'complete',
            'FAILED': 'failed',
            'CANCELLED': 'complete'
        }

        return status_list[status]

    def launch_job(self, job, workspace):
        # Need to generate a SLURM token (as a user) to launch a job
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        job_full_path = os.path.join(workspace_full_path, f'.{job.job_details["id"]}')

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.create_dir(job_full_path)
        self.resource_storage.set_ownership(job_full_path, user_info)

        token = self.get_user_token(user_info)

        # For pure testing, lets just set a var in the connection details.
        headers = {
            'Authorization': f'Token {self.connection_details.get("api_token")}',
            'Slurm-Token': token,
            'Slurm-User': user_info.external_username
        }

        body = {
            'script': job.get_script({"workspace_full_path": workspace_full_path}),
            'job': {
                'name': f'{workspace.name} {job.job_details["id"]}',
                'current_working_directory': job_full_path,
                'nodes': 1,
                'standard_output': os.path.join(job_full_path, f'slurm_{job.job_details["id"]}.out'),
                'standard_error': os.path.join(job_full_path, f'slurm_{job.job_details["id"]}_error.out'),
                'get_user_environment': 1,
                'environment': {
                    'PATH': '/bin/:/usr/bin/:/usr/local/bin/',
                    'LD_LIBRARY_PATH': '/lib/:/lib64/:/usr/local/lib'
                }
            }
        }

        slurm_response = http_r.post(f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/',
                                     json=body, headers=headers)

        if slurm_response.status_code != 200:
            raise APIException(slurm_response.text)

        slurm_response = slurm_response.json()

        if len(slurm_response['errors']):
            raise APIException(slurm_response['errors'], code=500)

        return slurm_response['job_id']

    def get_resource_job(self, job):
        workspace = job.workspace_id
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        token = self.get_user_token(user_info)

        headers = {
            'Authorization': f'Token {self.connection_details.get("api_token")}',
            'Slurm-Token': token,
            'Slurm-User': user_info.external_username
        }

        try:
            resource_job = http_r.get(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers).json()
            if len(resource_job['errors']):
                raise APIException(resource_job['errors'])

            resource_job = resource_job['jobs'][0]
            resource_job['status'] = self.translate_status(resource_job['job_state'])
            return resource_job
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}

    def get_job_core_hours(self, job):
        workspace = job.workspace_id
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        token = self.get_user_token(user_info)

        headers = {
            'Authorization': f'Token {self.connection_details.get("api_token")}',
            'Slurm-Token': token,
            'Slurm-User': user_info.external_username
        }

        try:
            resource_job = http_r.get(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers).json()
            if len(resource_job['errors']):
                raise APIException(resource_job['errors'])

            resource_job = resource_job['jobs'][0]
            time_running = resource_job.get('end_time') - resource_job.get('start_time')
            num_cores = resource_job.get('job_resources', {}).get('allocated_cpus', 0)
            core_seconds = time_running * num_cores

            # We use (end time - start time) * allocated cores which is the same as the wall time * cores.
            return core_seconds / 3600 if core_seconds != 0 else 0
        except Exception as e:
            print(repr(e))
            return 0

    def stop_job(self, job):
        user_info = self.resource_user_authentication.has_permission(job.workspace_id.user_id)

        token = self.get_user_token(user_info)

        # For pure testing, lets just set a var in the connection details.
        headers = {
            'Authorization': f'Token {self.connection_details.get("api_token")}',
            'Slurm-Token': token,
            'Slurm-User': user_info.external_username
        }

        try:
            resource_job = http_r.delete(
                f'{self.config.get("connection_details", {}).get("root_url")}/jobControl/{job.resource_job_id}',
                headers=headers).json()
            if len(resource_job['errors']):
                raise APIException(resource_job['errors'])

            return True
        except Exception as e:
            print(repr(e))
            return False

    def get_user_token(self, external_user):
        headers = {
            'Authorization': f'Token {self.connection_details.get("api_token")}',
            'Slurm-User': external_user.external_username,
            'Slurm-Lifespan': self.connection_details.get('token_lifespan')
        }
        response = http_r.get(f'{self.connection_details.get("root_url")}/getSlurmToken/',
                              headers=headers)

        if response.status_code not in [200, 201]:
            raise APIException(response.text)

        token = response.json()['slurm_token']
        return token
