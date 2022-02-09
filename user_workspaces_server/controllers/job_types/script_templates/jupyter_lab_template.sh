#!/bin/sh
# Let's assume that the module/virtualenv set-up can be moved else-where
# TODO: Make this configurable
virtualenv "$$_venv"
source activate "$$_venv"
pip install jupyterlab

# All we really need is this part

CONFIG_FILE="$(pwd)/$$_config.py"

# Generate Jupyter configuration file with secure file permissions
(
umask 077
cat > "${CONFIG_FILE}" << EOL
c.ServerApp.ip = '*'
c.ServerApp.open_browser = False
c.ServerApp.allow_origin = '*'
c.ServerApp.root_dir = "$(pwd)"
c.ServerApp.disable_check_xsrf = True
c.ServerApp.base_url = "/passthrough/$(hostname)/$$"
EOL
)

# Launch the Jupyter Notebook Server
set -x
jupyter lab --config="${CONFIG_FILE}" &> "$$_output.log"
