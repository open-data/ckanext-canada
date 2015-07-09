#!/bin/bash

function usage() {
    echo "Usage: ${0} CKAN-INI-FILE PORTAL-URL API-KEY \\"
    echo "    TARGET-DATASET:PACKAGE-ID ... [VIRTUAL-ENV-HOME]"
    echo
    echo "This script:"
    echo "- activates the virtual environment if specified"
    echo "- dumps datasets to .csv files"
    echo "- pushes these files to the portal as CKAN resources."
    echo
    echo "e.g., ${0} ../development.ini http://portal.gc.ca \\"
    echo "    00000000-0000-0000-0000-000000000000 ati:ati_id pd:pd_id"
    exit -1
}

LAST_TARG_ARG_IDX=$#
if [ "$#" -lt 4 ]
then
    usage
elif [[ ! "${!#}" =~ ":" ]]
then
    LAST_TARG_ARG_IDX=$(( $# - 1 ))
    VENV_HOME=$(echo ${!#} | sed -e 's:/$::')
    source ${VENV_HOME}/bin/activate
fi

# Establish bin directory
cd "$(dirname ${0})"
BIN_HOME=$(pwd)

# Record portal URL, API key
PORTAL_URL=${2}
API_KEY=${3}

# Set ini file
cd "$(dirname ${1})"
INI_FILE=$(basename ${1})
INI_PATH="$(pwd)/${INI_FILE}"

# Associate target datasets with ids
declare -A TARG_DS_MAP
for TARG_ARG in $(seq 4 ${LAST_TARG_ARG_IDX})
do
    TARG_DS_MAP["${!TARG_ARG%:*}"]="${!TARG_ARG#*:}"
done

TMPDIR=$(mktemp -t -d)

# Go to ckanext-recombinant, identify bona fide target datasets
cd "${BIN_HOME}/../../ckanext-recombinant"
CXR_HOME="$(pwd)"
TARGET_DATASETS=$(paster recombinant target-datasets -c "${INI_PATH}")

for TARG_DS in $(echo ${TARGET_DATASETS} | tr ' ' '\n')
do
    # Promote only those datasets specified on command line
    if [ -z "${TARG_DS_MAP[${TARG_DS}]}" ]
    then
        continue
    fi

    # Go to ckanext-recombinant, get dataset types for current target
    cd "${CXR_HOME}"
    DATASET_TYPES=$(echo $(paster recombinant dataset-types ${TARG_DS} -c "${INI_PATH}") | sed -e 's/.*: //')
    CSV_FILES=""
    for DS_TYPE in $(echo ${DATASET_TYPES} | tr ' ' '\n')
    do
        F="${TMPDIR}/${DS_TYPE}.csv"
        paster recombinant combine ${DS_TYPE} -c "${INI_PATH}" | \
	    "${BIN_HOME}/window_csv_results.py" > "${F}"
        CSV_FILES="${CSV_FILES} ${F}"
    done
    CSV_FILES=${CSV_FILES/ /}

    # Go to bin directory and upload files
    cd "${BIN_HOME}"
    python reg2portal.py "${INI_PATH}" "${PORTAL_URL}" "${API_KEY}" "${TARG_DS_MAP[${TARG_DS}]}" ${CSV_FILES}
done

# Clean up
/bin/rm -rf "${TMPDIR}"
