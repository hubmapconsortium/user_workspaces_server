from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import psutil
import subprocess
import os
import time
from django.core.files.base import ContentFile


class LocalResource(AbstractResource):
    def launch_job(self, job, workspace):
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        script_name = f"{str(time.time())}.sh"
        script_path = os.path.join(workspace_full_path, script_name)
        # Get the script content

        self.resource_storage.create_file(workspace_full_path, ContentFile(bytes(job.get_script(), 'utf-8'), name=script_name))

        user_info = self.resource_user_authentication.has_permission(workspace.user_id)

        self.resource_storage.set_ownership(script_path, user_info)

        os.chmod(script_path, 0o744)

        process = subprocess.Popen(['sudo', 'su', user_info.external_username, '-s', '/bin/bash', script_path],
                                   stdin=None, stdout=None, stderr=None, cwd=workspace_full_path,
                                   )
        return process.pid

    def get_job(self, resource_job_id):
        try:
            job = psutil.Process(resource_job_id)
            return job.as_dict()
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}
