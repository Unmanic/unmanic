#!/usr/bin/env bash
set -euo pipefail
set -E

INIT_DIR=${INIT_DIR:-/etc/cont-init.d}

log() {
    echo "**** (entrypoint) $*"
}

on_error() {
    local line_no=$1
    local cmd=$2
    local exit_code=$3
    local source_file=${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}
    log "Initialization failed in ${source_file}:${line_no}: ${cmd} (exit ${exit_code})"
    log "Sleeping 5 seconds before exiting to avoid rapid restarts"
    sleep 5
    exit 1
}
trap 'on_error ${LINENO} "${BASH_COMMAND}" $?' ERR

run_init_scripts() {
    if [[ ! -d "${INIT_DIR}" ]]; then
        log "Init directory ${INIT_DIR} not found; skipping init scripts"
        return
    fi

    shopt -s nullglob
    for script in "${INIT_DIR}"/*; do
        [[ -f "${script}" ]] || continue
        log "Sourcing ${script}"
        source "${script}"
    done
    shopt -u nullglob
}

ensure_runtime_paths() {
    mkdir -p \
        /config \
        /config/.unmanic \
        /tmp/unmanic

    if [[ "${EUID}" -eq 0 ]]; then
        chown -R 1000:1000 /config /tmp/unmanic || true
    fi
}

activate_venv() {
    local venv="${VIRTUAL_ENV:-/opt/venv}"

    if [[ -f "${venv}/bin/activate" ]]; then
        export VIRTUAL_ENV="${venv}"
        log "Activating virtualenv at ${VIRTUAL_ENV}"
        source "${VIRTUAL_ENV}/bin/activate"
    else
        log "No virtualenv found at ${venv}"
    fi
}

update_source_symlink() {
    if [[ ! -e /app/unmanic/service.py ]]; then
        return
    fi

    if [[ "${EUID}" -ne 0 ]]; then
        log "Not running as root, skipping source install symlink update"
        return
    fi

    log "Update container to running Unmanic from source"
    local venv="${VIRTUAL_ENV:-/opt/venv}"
    local python_version=$("${venv}/bin/python3" --version 2>&1 | grep -oP 'Python \K\d+\.\d+')
    local target="${venv}/lib/python${python_version:?}/site-packages/unmanic"
    if [[ -e "${target}" && ! -L "${target}" ]]; then
        log "Move container unmanic install"
        mv "${target}" "${target}-installed"
    fi
    ln -sf /app/unmanic "${target}"
}

main() {
    ensure_runtime_paths
    activate_venv
    run_init_scripts

    update_source_symlink

    if [[ "$1" == "/usr/bin/unmanic" || "$1" == "unmanic" ]]; then
        unmanic_params=()
        if [[ "${DEBUGGING:-}" == 'true' ]]; then
            unmanic_params+=(--dev)
        fi
        if [[ "${USE_TEST_SUPPORT_API:-}" == 'true' ]]; then
            unmanic_params+=(--dev-api=https://support-api.test.streamingtech.co.nz)
        fi
        set -- "$1" "${unmanic_params[@]}" "${@:2}"
    fi

    log "Starting: $*"
    exec "$@"
}

main "$@"
