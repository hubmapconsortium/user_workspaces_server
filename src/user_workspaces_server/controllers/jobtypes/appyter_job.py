import logging
import os
from datetime import datetime
from urllib import parse

from django.apps import apps
from django.template import loader

from user_workspaces_server import models
from user_workspaces_server.controllers.jobtypes.abstract_job import AbstractJob

logger = logging.getLogger(__name__)


class AppyterJob(AbstractJob):
    def __init__(self, config, job_details):
        super().__init__(config, job_details)
        self.script_template_name = "appyter_template.sh"
        self.notebook_path = job_details["job_details"]["request_job_details"].get(
            "notebook_path", "appyter.ipynb"
        )

    def get_script(self, template_params=None):
        template_config = {"job_id": self.job_details["id"], "notebook_path": self.notebook_path}

        logger.info(self.notebook_path)

        template_config.update(self.config)
        template_config.update(template_params)

        template = loader.get_template(f"script_templates/{self.script_template_name}")
        script = template.render(template_config)

        return script

    def status_check(self, job_model):
        output_file_name = f"AppyterJob_{job_model.id}_output.log"
        resource = apps.get_app_config("user_workspaces_server").main_resource

        if job_model.status == models.Job.Status.FAILED:
            return {
                "message": "This job has failed. Support team has been notified and will investigate the error."
            }

        # Check to see if we already have a connection url in place.
        if "connection_details" in job_model.job_details["current_job_details"]:
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
                f"Appyter output file {job_model.workspace_id.file_path}/.{job_model.id} missing."
            )
            return {"current_job_details": {"message": "Webserver not ready."}}

        url = ""

        for line in log_file:
            if "http" in line:
                url = parse.urlparse(line.split("] ")[1])
                break

        if not url:
            return {"current_job_details": {"message": "No url found."}}

        port = url.port
        hostname = url.hostname

        try:
            token = parse.parse_qs(url.query)["token"][0].strip()
        except KeyError:
            logger.warning("Token missing in Appyter output.")
            return {"current_job_details": {"message": "Token undefined."}}

        connection_string = f"{url.path}?token={token}"

        time_init = (
            datetime.now(job_model.datetime_start.tzinfo) - job_model.datetime_start
        ).total_seconds()

        return {
            "metrics": {
                "time_init": time_init,
            },
            "current_job_details": {
                "message": "Webserver ready.",
                "proxy_details": {
                    "hostname": hostname,
                    "port": port,
                    "path": connection_string,
                },
                "connection_details": {
                    "url_path": connection_string,
                },
            },
        }
