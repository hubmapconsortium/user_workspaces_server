from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import os
import time
from django.core.files.base import ContentFile
import requests as http_r


class SlurmAPIResource(AbstractResource):
    def launch_job(self, job, workspace):
        # Need to generate a SLURM token (as a user) to launch a job
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        script_name = f"{str(time.time())}.sh"
        script_path = os.path.join(workspace_full_path, script_name)
        # Get the script content

        self.resource_storage.create_file(workspace_full_path, ContentFile(bytes(job.get_script(), 'utf-8'), name=script_name))

        # TODO: Create an UAM for the slurm api since the token for that is different
        #  than the information for the psc user api
        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.set_ownership(script_path, user_info)

        os.chmod(script_path, 0o744)

        # For pure testing, lets just set a var in the connection details.
        headers = {'X-SLURM-USER-TOKEN': self.config.get("connection_details", {}).get("slurm_token", ""), 'X-SLURM-USER-NAME': f'{user_info.external_username}'}

        body = {
            'script': job.get_script(),
            'job': {
                'name': f'{workspace.name} {job.job_details["id"]}',
                'current_working_directory': workspace_full_path,
                'nodes': 1,
                'environment': {
                    'PATH': '/bin/:/usr/bin/:/usr/local/bin/',
                    'LD_LIBRARY_PATH': '/lib/:/lib64/:/usr/local/lib'
                }
            }
        }

        slurm_response = http_r.post(f'{self.config.get("connection_details", {}).get("root_url")}/job/submit', json=body, headers=headers).json()

        if len(slurm_response['errors']):
            raise Exception(slurm_response['errors'])

        print(slurm_response)

        return slurm_response.json()['job_id']

    def get_job(self, resource_job_id):
        try:
            job = http_r.get(f'{self.config.get("connection_details", {}).get("root_url")}/job/{resource_job_id}')
            print(job)
            return job.json()
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}
