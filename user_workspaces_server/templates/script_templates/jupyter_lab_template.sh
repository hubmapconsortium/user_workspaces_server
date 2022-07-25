#!/bin/bash
# Let's assume that the module/virtualenv set-up can be moved else-where

### Environment initialization

{% if module_manager == "lmod" %}
module load {{ modules|join:" " }}
{% elif module_manager == "virtualenv" %}
virtualenv -p {{ python_version }} "JupyterLabJob_{{ job_id }}_venv"
source "JupyterLabJob_{{ job_id }}_venv"
pip install {{ modules|join:" " }}
{% endif %}

# All we really need is this part

CONFIG_FILE="$(pwd)/JupyterLabJob_{{ job_id }}_config.py"

VERSION=$(jupyter lab --version)

# Generate Jupyter configuration file with secure file permissions
(
umask 077
cat > "${CONFIG_FILE}" << EOL
if ${VERSION:0:1} < 3:
  c.NotebookApp.ip = '*'
  c.NotebookApp.open_browser = False
  c.NotebookApp.allow_origin = '*'
  c.NotebookApp.notebook_dir = "$(pwd)"
  c.NotebookApp.disable_check_xsrf = True
  c.NotebookApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
else:
  c.ServerApp.ip = '*'
  c.ServerApp.open_browser = False
  c.ServerApp.allow_origin = '*'
  c.ServerApp.root_dir = "$(pwd)"
  c.ServerApp.disable_check_xsrf = True
  c.ServerApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
EOL
)

# Launch the Jupyter Notebook Server
set -x
jupyter lab --config="${CONFIG_FILE}" &> "JupyterLabJob_{{ job_id }}_output.log"
