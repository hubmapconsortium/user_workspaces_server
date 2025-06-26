#!/bin/bash
[[ {{ environment_name }} == .* ]] && ENV_NAME="{{ environment_name }}" || ENV_NAME=".{{ environment_name }}"
VENV_PATH="{{ workspace_full_path }}/${ENV_NAME}_venv"

echo "STARTED @ $(date)"
### Environment initialization
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
HOST=$(uname -n)

(
umask 077
cat > "$(pwd)/.env" << EOL
APPYTER_PORT=${PORT}
APPYTER_HOST=${HOST}
APPYTER_PREFIX=/passthrough/${HOST}/${PORT}
EOL
)


# Launch the Jupyter Notebook Server
set -x
python -m appyter --watch false --prefix "/passthrough/${HOST}/${PORT}" --port ${PORT} --host ${HOST} --proxy true --cwd "{{ workspace_full_path }}" "{{ notebook_path }}"