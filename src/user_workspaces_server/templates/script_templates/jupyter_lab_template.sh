#!/bin/bash
[[ {{ environment_name }} == .* ]] && ENV_NAME="{{ environment_name }}" || ENV_NAME=".{{ environment_name }}"
VENV_PATH="{{ workspace_full_path }}/${ENV_NAME}_venv"

echo "STARTED @ $(date)"

### Environment initialization
install_environment() {
  {% if module_manager == "tar" %}
    if [ ! -d "$VENV_PATH" ]; then
      mkdir -p "$VENV_PATH"
      tar -xf {{ tar_file_path }} -C "$VENV_PATH"
      echo "VENV COPIED @ $(date)"
      source "$VENV_PATH/bin/activate"
      conda-unpack
      echo "VENV UNPACKED @ $(date)"
      source "$VENV_PATH/bin/deactivate"
    fi
    source "$VENV_PATH/bin/activate"
  {% endif %}
  {% if module_manager == "lmod" %}
    module load {{ modules|join:" " }}
    {% if use_local_environment %}
      if [ ! -d "$VENV_PATH" ]; then
        export PYTHONNOUSERSITE=True
        conda create --prefix "$VENV_PATH" python={{ python_version }} -y
      fi
      source activate "$VENV_PATH"
      pip install {{ python_packages|join:" " }}
    {% endif %}
  {% elif module_manager == "virtualenv" %}
    if [ ! -d "$VENV_PATH" ]; then
      virtualenv -p {{ python_version }} "$VENV_PATH"
    fi
    source "$VENV_PATH/bin/activate"
    pip install {{ python_packages|join:" " }}
  {% endif %}
}

install_environment

### Jupyter configuration
CONFIG_FILE="$(pwd)/JupyterLabJob_{{ job_id }}_config.py"

random_number () {
  shuf -i ${1}-${2} -n 1
}

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

PORT=$(find_port)

set -x

# Check if Python is installed
if command -v python &>/dev/null; then
  # Check if Jupyter is installed in the Python environment
  if python -m jupyterlab --version &>/dev/null; then
    echo "Python & Jupyter installed"
  else
    # Delete the environment
    rm -rf "$VENV_PATH"
    install_environment
  fi
else
  # Delete the environment
  rm -rf "$VENV_PATH"
  install_environment
fi


# Generate Jupyter configuration file with secure file permissions based on JupyterLab version
VERSION=$(python -m jupyterlab --version)
(
umask 077
cat > "${CONFIG_FILE}" << EOL
if ${VERSION:0:1} < 3:
  c.NotebookApp.ip = '*'
  c.NotebookApp.open_browser = False
  c.NotebookApp.allow_origin = '*'
  c.NotebookApp.notebook_dir = "{{ workspace_full_path }}"
  c.NotebookApp.disable_check_xsrf = True
  c.NotebookApp.base_url = "/passthrough/$(hostname)/${PORT}"
  c.NotebookApp.port = ${PORT}
else:
  c.ServerApp.ip = '*'
  c.ServerApp.open_browser = False
  c.ServerApp.allow_origin = '*'
  c.ServerApp.root_dir = "{{ workspace_full_path }}"
  c.ServerApp.disable_check_xsrf = True
  c.ServerApp.base_url = "/passthrough/$(hostname)/${PORT}"
  c.ServerApp.port = ${PORT}
EOL
)

# Launch the Jupyter Notebook Server
export JUPYTER_DATA_DIR="$VENV_PATH/share/jupyter"
export SSL_CERT_FILE="$VENV_PATH/ssl/cert.pem"

python -m jupyterlab --config="${CONFIG_FILE}" &> "$(pwd)/JupyterLabJob_{{ job_id }}_output.log"