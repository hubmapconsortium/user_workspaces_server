from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import os
import time
from django.core.files.base import ContentFile
import requests as http_r


class SlurmAPIResource(AbstractResource):
    def translate_status(self, status):
        status_list = {
            'PENDING': 'pending',
            'RUNNING': 'running',
            'SUSPENDED': 'pending',
            'COMPLETING': 'running',
            'COMPLETED': 'complete',
            'FAILED': 'failed'
        }

        return status_list[status]

    def launch_job(self, job, workspace):
        # Need to generate a SLURM token (as a user) to launch a job
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)

        # TODO: Create an UAM for the slurm api since the token for that is different
        #  than the information for the psc user api
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        # For pure testing, lets just set a var in the connection details.
        headers = {'X-SLURM-USER-TOKEN': self.config.get("connection_details", {}).get("slurm_token", ""), 'X-SLURM-USER-NAME': f'{user_info.external_username}'}

        body = {
            'script': job.get_script(),
            'job': {
                'name': f'{workspace.name} {job.job_details["id"]}',
                'current_working_directory': workspace_full_path,
                'nodes': 1,
                'standard_output': f'{workspace_full_path}/slurm_{job.job_details["id"]}.out',
                'standard_error': f'{workspace_full_path}/slurm_{job.job_details["id"]}_error.out',
                'get_user_environment': 1,
                'environment': {
                    'PATH': '/bin/:/usr/bin/:/usr/local/bin/',
                    'LD_LIBRARY_PATH': '/lib/:/lib64/:/usr/local/lib'
                }
            }
        }

        slurm_response = http_r.post(f'{self.config.get("connection_details", {}).get("root_url")}/job/submit', json=body, headers=headers).json()

        if len(slurm_response['errors']):
            raise Exception(slurm_response['errors'])

        return slurm_response['job_id']

    def get_resource_job(self, job):
        workspace = job.workspace_id
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)
        headers = {'X-SLURM-USER-TOKEN': self.config.get("connection_details", {}).get("slurm_token", ""),
                   'X-SLURM-USER-NAME': f'{user_info.external_username}'}

        try:
            resource_job = http_r.get(f'{self.config.get("connection_details", {}).get("root_url")}/job/{job.resource_job_id}', headers=headers).json()
            if len(resource_job['errors']):
                raise Exception(resource_job['errors'])

            resource_job = resource_job['jobs'][0]
            resource_job['status'] = self.translate_status(resource_job['job_state'])
            return resource_job
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}
