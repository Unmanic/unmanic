#!/usr/bin/env bash

__script_path=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd );
__project_root=$(realpath ${__script_path}/..);

function docker_env {
    docker pull lsiobase/ubuntu:focal
    docker run --rm -ti \
        --workdir=/app \
        --entrypoint='' \
        -v "${__project_root}/":"/app/" \
        josh5/unmanic:latest \
        ./devops/update-docker-packages.sh --print
}


function print_updated_packages {
    runtime_packages=(
        "libmediainfo0v5"
    )
    intel_compute_runtime_packages=(
        "libigdgmm12"
        "libigdfcl1"
        "libigc1"
        "intel-opencl-icd"
        "intel-igc-cm"
        "intel-level-zero-gpu"
    )

    apt-get update
    apt list --upgradable 2> /dev/null 1> /tmp/apt-updates.txt

    echo
    echo "Runtime package updates"
    echo
    for package in ${runtime_packages[@]}; do
        update_version=$(cat /tmp/apt-updates.txt | grep "${package}/" | awk '{print $2}');
        if [[ -z ${update_version} ]]; then
            if [[ ${1:-X} == 'all' ]]; then
                current_version=$(dpkg -s "${package}" | grep Version | awk '{print $2}')
                echo "            ${package}=${current_version} \\"
            fi
            continue
        fi
        echo "            ${package}=${update_version} \\"
    done
    echo

    echo
    echo "Intel Compute Runtime package updates"
    echo
    for package in ${intel_compute_runtime_packages[@]}; do
        update_version=$(cat /tmp/apt-updates.txt | grep "${package}/" | awk '{print $2}');
        if [[ -z ${update_version} ]]; then
            if [[ ${1:-X} == 'all' ]]; then
                current_version=$(dpkg -s "${package}" | grep Version | awk '{print $2}')
                echo "                    ${package}=${current_version} \\"
            fi
            continue
        fi
        echo "                    ${package}=${update_version} \\"
    done
    echo
}

# RUN
while getopts "h:-:" arg; do
  case $arg in
    h )  usage; exit 0 ;;
    - )  LONG_OPTARG="${OPTARG#*=}"
         case $OPTARG in
           print )  print_updated_packages; exit 0 ;;
           '' )     break ;; # "--" terminates argument processing
           * )      die "Illegal option --$OPTARG" ;;
         esac ;;
    \? ) exit 2 ;;
  esac
done
shift $((OPTIND-1))

docker_env
