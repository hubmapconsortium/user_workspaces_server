import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from random import random
from typing import Any, Callable, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import HTTPError

from tests.stress_testing_fixtures import get_workspace_data

# For consistent error logging
JOBS_KEY = "jobs"
WORKSPACES_KEY = "workspaces"
GET_KEY = "get"


class UWSStressTester:
    """
    Send repeated requests to UWS endpoint.
    Use with caution and warn workspaces collaborators first!
    """

    def __init__(
        self,
        workspace_id: int,
        token: str,
        env: str = "dev",
        with_linked_datasets: bool = False,
        linked_dataset_uuids: Optional[list[int]] = None,
        globus_token: str = "",
    ):
        self.workspace_id = workspace_id
        self.token = token
        self.env = env
        self.with_linked_datasets = with_linked_datasets
        self.linked_dataset_uuids = linked_dataset_uuids if linked_dataset_uuids else []
        self.globus_token = globus_token
        self.jobs_stopped = []
        self.workspaces_deleted = []
        self.successes = defaultdict(list)
        self.errors = defaultdict(list)
        self.headers = {
            "UWS-Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    def get_url_for_env(self, middle_parts: str, random_str: bool = True) -> str:
        base_urls = {
            "dev": "https://workspaces-api.dev.hubmapconsortium.org/",
            "local": "http://0.0.0.0:5050/",
        }
        mid_url = middle_parts + "/" if not middle_parts.endswith("/") else middle_parts
        if not random_str:
            with_params = mid_url
        else:
            with_params = f"{mid_url}?random={random()}"
        return urljoin(base_urls.get(self.env, ""), with_params)

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

    def put_job_start(self, workspace_id: int) -> requests.Response:
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
        url = self.get_url_for_env(f"workspaces/{workspace_id}/start/")
        response = requests.put(
            url=url,
            headers=self.headers,
            data=json.dumps(body),
        )
        return response

    def post_create_workspace(self) -> requests.Response:
        body: dict[str, Any] = {
            "name": f"Test Workspace {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}",
            "description": "Test workspace created durings stress testing",
            "default_job_type": "jupyter_lab_gpu_common_packages",
        }
        body["workspace_details"] = get_workspace_data(
            self.globus_token, self.with_linked_datasets, self.linked_dataset_uuids
        )
        url = self.get_url_for_env("workspaces/", random_str=False)
        response = requests.post(
            url=url,
            headers=self.headers,
            data=json.dumps(body),
        )
        return response

    def get_jobs_info(self) -> requests.Response:
        url = self.get_url_for_env("jobs/", random_str=False)
        response = requests.get(
            url=url,
            headers=self.headers,
        )
        return response

    #####################
    # Initiate requests #
    #####################

    def start_job(self, workspace_id: Optional[int] = None) -> Optional[int]:
        if not workspace_id:
            workspace_id = self.workspace_id
        try:
            response = self.put_job_start(workspace_id)
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

    def create_workspace(self):
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
        for _ in range(num):
            if len(self.errors[WORKSPACES_KEY]) < 10:
                func()

    def spam(
        self,
        num_workspaces: int = 0,
        num_jobs: int = 0,
        num_requests: int = 0,
    ):
        map = [
            (
                num_workspaces,
                WORKSPACES_KEY,
                self.create_workspace,
            ),
            (num_jobs, JOBS_KEY, self.start_job),
            (num_requests, GET_KEY, self.get_jobs),
        ]
        with ThreadPoolExecutor(max_workers=4) as executor:
            for num, key, func in map:
                executor.submit(self.spam_x, num, key, func)

    def create_and_start_workspaces(self, num_workspaces):
        errors = 0
        for _ in range(num_workspaces):
            if not (workspace_id := self.create_workspace()):
                errors += 1
                continue
            if not self.start_job(workspace_id):
                errors += 1

    ###########
    # Cleanup #
    ###########

    def cleanup(self):
        self.stop_jobs()
        self.delete_workspaces()

    def delete_workspaces(self):
        for workspace_id in self.successes[WORKSPACES_KEY].copy():
            delete_workspace = requests.delete(
                self.get_url_for_env(f"workspaces/{workspace_id}/"),
                headers=self.headers,
            )
            try:
                delete_workspace.raise_for_status()
            except HTTPError as e:
                print(delete_workspace.json())
                if delete_workspace.status_code == 404:
                    self.errors[WORKSPACES_KEY].append(
                        f"Workspace {workspace_id} does not exist, already deleted?"
                    )
                else:
                    self.errors[WORKSPACES_KEY].append(e.strerror)
                    continue
            self.successes[WORKSPACES_KEY].remove(workspace_id)

    def stop_jobs(self):
        for job_id in self.successes[JOBS_KEY]:
            url = self.get_url_for_env(f"jobs/{job_id}/stop/")
            response = requests.put(url, headers=self.headers)
            if response.json().get("message") == "This job is not running or pending.":
                print(f"Job {job_id} already stopped.")
            else:
                response.raise_for_status()
                print(f"Job {job_id} stopped.")
            self.jobs_stopped.append(job_id)
