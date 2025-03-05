import json
from collections import defaultdict
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urljoin

import requests

JOBS_KEY = "jobs"
WORKSPACES_KEY = "workspaces"
GET_KEY = "get"


class UWSStressTester:
    """
    Send repeated requests to UWS endpoint.
    Use with caution and warn workspaces collaborators first!
    """

    def __init__(self, workspace_id: str, token: str, env: str = "dev"):
        self.workspace_id = workspace_id
        self.token = token
        self.env = env
        self.jobs_stopped = []
        self.workspaces_deleted = []
        self.successes = defaultdict(list)
        self.errors = defaultdict(list)
        self.headers = {
            "UWS-Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    @property
    def get_url_for_env(self) -> str:
        urls = {
            "dev": "https://workspaces-api.dev.hubmapconsortium.org/",
            "local": "http://0.0.0.0:5050/",
        }
        return urls.get(self.env, "")

    @property
    def report(self):
        print(
            f"""
              Jobs started: {len(self.successes[JOBS_KEY])}
              {self.successes[JOBS_KEY]}
              Workspaces started: {len(self.successes[WORKSPACES_KEY])}
              {self.successes[WORKSPACES_KEY]}
              Get requests: {len(self.successes[GET_KEY])}
              Job errors: {len(self.errors[JOBS_KEY])}
              Workspace errors: {len(self.errors[WORKSPACES_KEY])}
              Get errors: {len(self.errors[GET_KEY])}
              Jobs stopped: {len(self.jobs_stopped)}
              {self.jobs_stopped}
              """
        )

    ############
    # Requests #
    ############

    def put_job_start(self) -> requests.Response:
        body = {
            "job_type": "jupyter_lab",
            "job_details": {},
            "resource_options": {
                "num_cpus": 1,
                "memory_mb": 8192,
                "time_limit_minutes": 180,
                "gpu_enabled": False,
            },
        }
        url = urljoin(self.get_url_for_env, f"workspaces/{self.workspace_id}/start/")
        response = requests.put(
            url=url,
            headers=self.headers,
            data=json.dumps(body),
        )
        return response

    def post_create_workspace(self) -> requests.Response:
        body = {
            "name": "Test Workspace",
            "description": f"Test workspace created durings stress testing {datetime.now()}",
            "workspace_details": {
                "files": [
                    {
                        "name": "jupyter_notebooks/blank.ipynb",
                        "content": '{\n "cells": [\n  {\n   "cell_type": "markdown",\n   "id": "e399c39d",\n   "metadata": {},\n   "source": [\n    "Test workspace!"\n   ]}]}',
                    }
                ]
            },
        }
        url = urljoin(self.get_url_for_env, f"workspaces/")
        response = requests.post(
            url=url,
            headers=self.headers,
            data=json.dumps(body),
        )
        return response

    def get_jobs_info(self) -> requests.Response:
        url = urljoin(self.get_url_for_env, f"jobs/")
        response = requests.get(
            url=url,
            headers=self.headers,
        )
        return response

    #####################
    # Initiate requests #
    #####################

    def start_job(self) -> Optional[int]:
        try:
            response = self.put_job_start()
            response.raise_for_status()
        except Exception as e:
            self.errors[JOBS_KEY].append(e)
            return
        job_id = response.json().get("data", {}).get("job", {}).get("id")
        print(f"Job {job_id} started at {datetime.now()}")
        self.successes[JOBS_KEY].append(job_id)
        return job_id

    def get_jobs(self):
        try:
            response = self.get_jobs_info()
            response.raise_for_status()
        except Exception as e:
            self.errors[GET_KEY].append(e)
            return
        self.successes[GET_KEY].append(True)
        print(f"Get request succeeded at {datetime.now()}")

    def create_workspaces(self):
        try:
            response = self.post_create_workspace()
            response.raise_for_status()
        except Exception as e:
            self.errors[WORKSPACES_KEY].append(e)
            return
        workspace_id = response.json().get("data", {}).get("workspace", {}).get("id")
        print(f"Workspace {workspace_id} created at {datetime.now()}")
        self.successes[WORKSPACES_KEY].append(workspace_id)
        return workspace_id

    #########
    # Spam! #
    #########

    def spam_x(self, num: int, key: str, func: Callable):
        print(f"Spam {key} x {num}")
        print(f"Time started: {datetime.now()}")
        for _ in range(num):
            if len(self.errors[WORKSPACES_KEY]) < 10:
                func()
        print(f"Time stopped: {datetime.now()}")

    def spam(self, num_workspaces: int = 0, num_jobs: int = 0, num_requests: int = 0):
        map = [
            (num_workspaces, WORKSPACES_KEY, self.create_workspaces),
            (num_jobs, JOBS_KEY, self.start_job),
            (num_requests, GET_KEY, self.get_jobs),
        ]
        for num, key, func in map:
            self.spam_x(num, key, func)

    ###########
    # Cleanup #
    ###########

    # def cleanup(self):
    #     self.stop_jobs()
    #     self.delete_workspaces()
    #
    # experimental
    def delete_workspaces(self):
        for workspace_id in self.successes[WORKSPACES_KEY]:
            delete_workspace = requests.delete(
                urljoin(self.get_url_for_env, f"workspaces/{workspace_id}/")
            )
            delete_workspace.raise_for_status()
            print(delete_workspace.json())

    def stop_jobs(self):
        for job_id in self.successes[JOBS_KEY]:
            url = urljoin(self.get_url_for_env, f"jobs/{job_id}/stop/")
            response = requests.put(url, headers=self.headers)
            if response.json().get("message") == "This job is not running or pending.":
                print(f"Job {job_id} already stopped.")
            else:
                response.raise_for_status()
                print(f"Job {job_id} stopped.")
            self.jobs_stopped.append(job_id)
