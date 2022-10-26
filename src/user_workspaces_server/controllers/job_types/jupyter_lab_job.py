from user_workspaces_server.controllers.job_types.abstract_job import AbstractJob
import os
from django.apps import apps
from urllib import parse
from django.template import loader
import logging

logger = logging.getLogger(__name__)


class JupyterLabJob(AbstractJob):
    def __init__(self, config, job_details):
        super().__init__(config, job_details)
        self.script_template_name = "jupyter_lab_template.sh"

    def get_script(self, template_params=None):
        template_config = {"job_id": self.job_details["id"]}
        template_config.update(self.config)
        template_config.update(template_params)

        template = loader.get_template(f"script_templates/{self.script_template_name}")
        script = template.render(template_config)

        return script

    def status_check(self, job_model):
        output_file_name = f"JupyterLabJob_{job_model.id}_output.log"
        resource = apps.get_app_config("user_workspaces_server").main_resource

        # Check to see if we already have a connection url in place.
        if "connection_params" in job_model.job_details["current_job_details"]:
            return {}

        try:
            with open(
                os.path.join(
                    resource.resource_storage.root_dir,
                    job_model.workspace_id.file_path,
                    f".{job_model.id}",
                    output_file_name,
                )
            ) as f:
                log_file = f.readlines()
        except FileNotFoundError:
            logger.warning(
                f"JupyterLab output file {job_model.workspace_id.file_path}/.{job_model.id} missing."
            )
            return {"message": "Webserver not ready."}

        url = ""

        for line in log_file:
            if "http" in line:
                url = parse.urlparse(line.split("] ")[1])
                break

        if not url:
            return {"message": "No url found."}

        port = url.port
        hostname = url.hostname

        try:
            token = parse.parse_qs(url.query)["token"][0].strip()
        except KeyError:
            logger.warning("Token missing in JupyterLab output.")
            return {"message": "Token undefined."}

        connection_string = f"{url.path}?token={token}"

        return {
            "message": "Webserver ready.",
            "proxy_details": {
                "hostname": hostname,
                "port": port,
                "path": connection_string,
            },
            "connection_details": {
                "url_path": connection_string,
            },
        }
