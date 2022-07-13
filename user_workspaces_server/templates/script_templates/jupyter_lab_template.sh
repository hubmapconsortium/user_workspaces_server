#!/bin/bash
# TODO: Need to make this work with Slurm.
# Let's assume that the module/virtualenv set-up can be moved else-where

### BRIDGES2 BLOCK ###
module load anaconda3
### END BRIDGES2 BLOCK ###


# TODO: Make this configurable
### LOCAL BLOCK ###
#virtualenv -p python3.8 "JupyterLabJob_{{ job_id }}_venv"
#source "JupyterLabJob_{{ job_id }}_venv/bin/activate"
#pip install jupyterlab
### END LOCAL BLOCK ###

# All we really need is this part

CONFIG_FILE="$(pwd)/JupyterLabJob_{{ job_id }}_config.py"

# Generate Jupyter configuration file with secure file permissions
(
umask 077
cat > "${CONFIG_FILE}" << EOL
c.NotebookApp.ip = '*'
c.NotebookApp.open_browser = False
c.NotebookApp.allow_origin = '*'
c.NotebookApp.root_dir = "$(pwd)"
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
#c.ServerApp.ip = '*'
#c.ServerApp.open_browser = False
#c.ServerApp.allow_origin = '*'
#c.ServerApp.root_dir = "$(pwd)"
#c.ServerApp.disable_check_xsrf = True
#c.ServerApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
EOL
)

# Launch the Jupyter Notebook Server
set -x
jupyter lab --config="${CONFIG_FILE}" &> "JupyterLabJob_{{ job_id }}_output.log"
