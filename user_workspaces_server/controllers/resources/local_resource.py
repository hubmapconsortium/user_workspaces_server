from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import psutil
import subprocess
import os
import time
from django.core.files.base import ContentFile


class LocalResource(AbstractResource):
    def translate_status(self, status):
        status_list = {
            'sleeping': 'running',
            'running': 'running',
            'zombie': 'complete',
            'complete': 'complete',
            'dead': 'failed'
        }

        return status_list[status]

    def launch_job(self, job, workspace):
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        job_full_path = os.path.join(workspace_full_path, f'.{job.job_details["id"]}')
        script_name = f"{str(time.time())}.sh"
        script_path = os.path.join(job_full_path, script_name)
        # Get the script content

        self.resource_storage.create_file(job_full_path, ContentFile(bytes(job.get_script(
            {"workspace_full_path": workspace_full_path}), 'utf-8'), name=script_name))

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.set_ownership(job_full_path, user_info)
        self.resource_storage.set_ownership(script_path, user_info)

        os.chmod(script_path, 0o744)

        process = subprocess.Popen(['sudo', 'su', user_info.external_username, '-s', '/bin/bash', script_path],
                                   stdin=None, stdout=None, stderr=None, cwd=job_full_path,
                                   )
        return process.pid

    def get_resource_job(self, job):
        resource_job_id = job.resource_job_id
        try:
            resource_job = psutil.Process(resource_job_id).as_dict()
            resource_job['status'] = self.translate_status(resource_job['status'])
            return resource_job
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}
