#!/bin/bash

### Environment initialization
{% if module_manager == "lmod" %}
module load {{ modules|join:" " }}
{% if use_local_environment %}
export PYTHONNOUSERSITE=True
conda create --prefix "$(pwd)/JupyterLabJob_{{ job_id }}_venv" python={{ python_version }} -y
source activate "$(pwd)/JupyterLabJob_{{ job_id }}_venv"
pip install {{ python_packages|join:" " }}
{% endif %}
{% elif module_manager == "virtualenv" %}
virtualenv -p {{ python_version }} "$(pwd)/JupyterLabJob_{{ job_id }}_venv"
source "$(pwd)/JupyterLabJob_{{ job_id }}_venv/bin/activate"
pip install {{ python_packages|join:" " }}
{% endif %}

### Jupyter configuration
CONFIG_FILE="$(pwd)/JupyterLabJob_{{ job_id }}_config.py"

VERSION=$(python -m jupyterlab --version)

port_used_python() {
  python -c "import socket; socket.socket().connect(('$1',$2))" >/dev/null 2>&1
}

port_used_python3() {
  python3 -c "import socket; socket.socket().connect(('$1',$2))" >/dev/null 2>&1
}

port_used_nc(){
  nc -w 2 "$1" "$2" < /dev/null > /dev/null 2>&1
}

port_used_lsof(){
  lsof -i :"$2" >/dev/null 2>&1
}

port_used_bash(){
  local bash_supported=$(strings /bin/bash 2>/dev/null | grep tcp)
  if [ "$bash_supported" == "/dev/tcp/*/*" ]; then
    (: < /dev/tcp/$1/$2) >/dev/null 2>&1
  else
    return 127
  fi
}

# Check if port $1 is in use
port_used () {
  local port="${1#*:}"
  local host=$((expr "${1}" : '\(.*\):' || echo "localhost") | awk 'END{print $NF}')
  local port_strategies=(port_used_nc port_used_lsof port_used_bash port_used_python port_used_python3)

  for strategy in ${port_strategies[@]};
  do
    $strategy $host $port
    status=$?
    if [[ "$status" == "0" ]] || [[ "$status" == "1" ]]; then
      return $status
    fi
  done

  return 127
}

# Find available port in range [$2..$3] for host $1
# Default: [2000..65535]
find_port () {
  local host="${1:-localhost}"
  local port=$(random_number "${2:-2000}" "${3:-65535}")
  while port_used "${host}:${port}"; do
    port=$(random_number "${2:-2000}" "${3:-65535}")
  done
  echo "${port}"
}

port=$(find_port)

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
  c.NotebookApp.port = $(port)
else:
  c.ServerApp.ip = '*'
  c.ServerApp.open_browser = False
  c.ServerApp.allow_origin = '*'
  c.ServerApp.root_dir = "{{ workspace_full_path }}"
  c.ServerApp.disable_check_xsrf = True
  c.ServerApp.base_url = "/passthrough/$(hostname)/{{ job_id }}"
  c.ServerApp.port = $(port)
EOL
)

# Launch the Jupyter Notebook Server
set -x
python -m jupyterlab --config="${CONFIG_FILE}" &> "$(pwd)/JupyterLabJob_{{ job_id }}_output.log"
