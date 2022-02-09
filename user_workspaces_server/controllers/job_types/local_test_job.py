from user_workspaces_server.controllers.job_types.abstract_job import AbstractJob
import os

class LocalTestJob(AbstractJob):
    def __init__(self, config, job_details):
        super().__init__(config, job_details)
        self.script_template_name = 'local_test_template.sh'

    def get_script(self):
        with open(os.path.join(
                os.path.abspath(os.getcwd()), 'user_workspaces_server/controllers/job_types/script_templates',
                self.script_template_name), 'r') as f:

            script = f.read()

        return script

    def status_check(self, job_model):
        return {}
