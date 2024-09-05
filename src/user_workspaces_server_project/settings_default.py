from .settings import *

API_USER_AUTHENTICATION = "main_auth"
MAIN_STORAGE = "main_storage"
MAIN_RESOURCE = "main_resource"

AVAILABLE_USER_AUTHENTICATION = {
    API_USER_AUTHENTICATION: {
      "name": "Local Token Auth",
      "user_authentication_type": "LocalUserAuthentication",
      "connection_details": {
          "create_external_users": True,
          "operating_system": "linux"
      }
    }
  }
AVAILABLE_STORAGE = {
    MAIN_STORAGE: {
      "name": "Local File Storage",
      "storage_type": "LocalFileSystemStorage",
      "user_authentication": API_USER_AUTHENTICATION,
      "root_dir": ".",
      "connection_details": {}
    }
  }

AVAILABLE_RESOURCES = {
    MAIN_RESOURCE: {
      "name": "Local Resource",
      "resource_type": "LocalResource",
      "storage": MAIN_STORAGE,
      "user_authentication": API_USER_AUTHENTICATION,
      "passthrough_domain": "127.0.0.1:8000",
      "connection_details": {}
    }
  }

AVAILABLE_JOB_TYPES = {
    "jupyter_lab": {
      "name": "Jupyter Lab",
      "job_type": "JupyterLabJob",
      "environment_details": {
        MAIN_RESOURCE: {
          "python_version": "python3.8",
          "module_manager": "virtualenv",
          "modules": [
            "jupyterlab"
          ],
          "time_limit": "60",
          "environment_name": "JupyterLabJob"
        }
      }
    },
    "local_test_job": {
      "name": "Local Test Job",
      "job_type": "LocalTestJob",
      "environment_details": {
        MAIN_RESOURCE: {
        }
      }
    }
  }
