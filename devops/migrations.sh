#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )";

if [[ ! -x $(command -v pw_migrate) ]]; then
    echo "Missing dependency 'pw_migrate'.";
    echo "Ensure requirements.txt is satisfied first.";
    echo
    echo "Run:";
    echo "python3 -m pip install --user --upgrade -r $(realpath ${SCRIPT_DIR}/../requirements.txt)";
    echo
    exit 1;
fi

DATABASE_FILE=$(realpath "${HOME}/.unmanic/config/unmanic.db");
TEST_DATABASE_FILE=$(realpath "${SCRIPT_DIR}/../tests/tmp/config/.unmanic/config/unmanic.db");
if [[ -f ${TEST_DATABASE_FILE} ]]; then
    DATABASE_FILE=${TEST_DATABASE_FILE}
fi
MIGRATIONS_PATH=$(realpath "${SCRIPT_DIR}/../unmanic/migrations");
NAME=$(echo ${@} | awk '{print tolower($0)}' | tr ' ' '_');


# Parse args
ARGS="--database=sqlite:///${DATABASE_FILE} --directory=${MIGRATIONS_PATH}"
COMMAND=""
for ARG in ${@}; do
    if [[ "${ARG}" == "--help" || "${ARG}" == "-h" ]]; then
        pw_migrate --help;
        echo
        exit 0;
    elif [[ "${ARG}" == "create" ]]; then
        COMMAND="create";
        continue;
    elif [[ "${ARG}" == "list" ]]; then
        COMMAND="list";
        continue;
    elif [[ "${ARG}" == "merge" ]]; then
        COMMAND="merge";
        continue;
    elif [[ "${ARG}" == "migrate" || "${ARG}" == "run" ]]; then
        COMMAND="migrate";
        continue;
    elif [[ "${ARG}" == "rollback" ]]; then
        COMMAND="rollback";
        continue;
    fi
    ARGS="${ARGS} ${ARG}";
done

echo "pw_migrate ${COMMAND} ${ARGS}";
pw_migrate ${COMMAND} ${ARGS};
