from django.template import loader

from user_workspaces_server.controllers.job_types.abstract_job import AbstractJob


class LocalTestJob(AbstractJob):
    def __init__(self, config, job_details):
        super().__init__(config, job_details)
        self.script_template_name = "local_test_template.sh"

    def get_script(self, template_params=None):
        template = loader.get_template(f"script_templates/{self.script_template_name}")
        script = template.render({"job_id": self.job_details["id"]})

        return script

    def status_check(self, job_model):
        return {}
