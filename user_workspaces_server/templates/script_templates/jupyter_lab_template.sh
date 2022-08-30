#!/bin/bash

### Environment initialization
{% if module_manager == "lmod" %}
module load {{ modules|join:" " }}
{% if environment_name is not none}
conda create --prefix $(pwd) -n JupyterLabJob__{{ job_id }}__venv python={{ python_version }}
conda activate $(pwd)/JupyterLabJob__{{ job_id }}__venv
pip install {{ modules|join:" " }}
{% endif %}
{% elif module_manager == "virtualenv" %}
virtualenv -p {{ python_version }} "$(pwd)/JupyterLabJob_{{ job_id }}_venv"
source "$(pwd)/JupyterLabJob_{{ job_id }}_venv/bin/activate"
pip install {{ modules|join:" " }}
{% endif %}

### Jupyter configuration
CONFIG_FILE="$(pwd)/JupyterLabJob_{{ job_id }}_config.py"

VERSION=$(jupyter lab --version)

# Generate Jupyter configuration file with secure file permissions based on JupyterLab version
(
umask 077
cat > "${CONFIG_FILE}" << EOL
if ${VERSION:0:1} < 3:
  c.NotebookApp.ip = '*'
  c.NotebookApp.open_browser = False
  c.NotebookApp.allow_origin = '*'
  c.NotebookApp.notebook_dir = "{{ workspace_full_path }}"
  c.NotebookApp.disable_check_xsrf = True
  c.NotebookApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
else:
  c.ServerApp.ip = '*'
  c.ServerApp.open_browser = False
  c.ServerApp.allow_origin = '*'
  c.ServerApp.root_dir = "{{ workspace_full_path }}"
  c.ServerApp.disable_check_xsrf = True
  c.ServerApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
EOL
)

# Launch the Jupyter Notebook Server
set -x
jupyter lab --config="${CONFIG_FILE}" &> "$(pwd)/JupyterLabJob_{{ job_id }}_output.log"
