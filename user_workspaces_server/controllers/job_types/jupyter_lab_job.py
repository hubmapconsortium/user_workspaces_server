from user_workspaces_server.controllers.job_types.abstract_job import AbstractJob


class JupyterLabJob(AbstractJob):
    # TODO: Come up with a better way of doing this. Just a string is not good enough.

    def __init__(self):
        self.script = "#!/bin/sh\nvirtualenv venv\nsource activate venv\npip install jupyterlab\njupyter lab --no-browser > ./output.log"

    def get_script(self):
        return self.script

    # TODO: This should check for a connection.json file in the workspace where the job is launched.
    def status_check(self):
        pass
