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
                    ".env",
                )
            ) as f:
                env_file = f.readlines()
        except FileNotFoundError:
            logger.warning(
                f"Appyter output file {job_model.workspace_id.file_path}/.{job_model.id} missing."
            )
            return {"current_job_details": {"message": "Webserver not ready."}}

        env = {}

        for line in env_file:
            line_split = line.split("=")
            # 7 is the magic number since it's the length of 'APPYTER'
            env[line_split[0][7:].strip()] = line_split[1].strip()

        port = env["PORT"]
        hostname = env["HOST"]
        connection_string = env["PREFIX"]

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
