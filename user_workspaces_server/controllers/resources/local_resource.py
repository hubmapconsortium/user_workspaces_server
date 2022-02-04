from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
import psutil
import subprocess
import os
import datetime


class LocalResource(AbstractResource):
    def launch_job(self, job, workspace):
        workspace_full_path = os.path.join(self.resource_storage.root_dir, workspace.file_path)
        script_name = f"{str(datetime.datetime.now())}.sh"
        script_path = os.path.join(workspace_full_path, script_name)
        # Get the script content
        with open(script_path, 'w') as script:
            script.write(job.script)

        os.chmod(script_path, 0o744)
        process = subprocess.Popen(script_path, stdin=None, stdout=None, stderr=None, cwd=workspace_full_path)
        return process.pid

    def get_job(self, resource_job_id):
        try:
            job = psutil.Process(resource_job_id)
            return job.as_dict()
        except Exception as e:
            print(repr(e))
            return {'status': 'complete'}
