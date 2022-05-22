#!/usr/bin/env bash
###
# File: local_dev_denv.sh
# Project: devops
# File Created: Tuesday, 17th May 2022 6:55:32 pm
# Author: Josh.5 (jsunnex@gmail.com)
# -----
# Last Modified: Tuesday, 17th May 2022 8:05:25 pm
# Modified By: Josh.5 (jsunnex@gmail.com)
###
#
# After running this script you can run unmanic with the following commands:
#
#   source venv/bin/activate
#   export HOME_DIR="${PWD}/dev_environment"
#   unmanic
#

script_path=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project_root=$(readlink -e ${script_path}/..)

pushd "${project_root}" || exit 1

# Checkout all submodules
git submodule update --init --recursive

# Ensure we have created a venv
if [[ ! -e venv/bin/activate ]]; then
    python3 -m venv venv
fi

# Active the venv
source venv/bin/activate

# Install all Unmanic requirements
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt

# Install the project to the venv
devops/frontend_install.sh
python3 setup.py develop

popd || exit 1
