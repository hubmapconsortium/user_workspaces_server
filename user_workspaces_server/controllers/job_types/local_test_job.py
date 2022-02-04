from user_workspaces_server.controllers.job_types.abstract_job import AbstractJob


class LocalTestJob(AbstractJob):
    def __init__(self):
        self.script = "#!/bin/sh\necho 'Hello World' > ./output.log\nsleep 10"

    def get_script(self):
        pass

    def status_check(self):
        pass
