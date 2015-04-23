#!/bin/bash

function usage() {
    echo "Usage: ${0} CKAN-INI-FILE \\"
    echo "    TARGET-DATASET:PACKAGE-ID ... [VIRTUAL-ENV-HOME]"
    echo
    echo "This script:"
    echo "- activates virtual environment if specified"
    echo "- pushes datasets from .csv files to the solr core"
    echo
    echo "e.g., ${0} ../development.ini ati:ati_id pd:pd_id /opt/my-venv"

    exit -1
}

function log() {
    DT=$(date +'%F %T')
    LEVEL=${1}
    MSG=${2}
    echo ${DT} ${LEVEL} [$(basename "${0}")] ${MSG}
}

LAST_TARG_ARG_IDX=$#
if [ "$#" -lt 2 ]
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

# Set .ini file, get port of operation from [server:main] section
cd "$(dirname ${1})"
INI_FILE=$(basename ${1})
INI_PATH="$(pwd)/${INI_FILE}"
INI_PORT=$(sed -n -e '/^\[server:main\]/,/^\[.*\]/p' ${INI_PATH} | sed -n 's/^ *port *= *\([^ ]*.*\)/\1/p')
INI_PORT=${INI_PORT%% *}

# Associate target datasets with ids
declare -A TARG_DS_MAP
for TARG_ARG in $(seq 2 ${LAST_TARG_ARG_IDX})
do
    TARG_DS_MAP["${!TARG_ARG%:*}"]="${!TARG_ARG#*:}"
done

TMPDIR=$(mktemp -t -d)

# Record ckanext-canada home
cd "${BIN_HOME}/.."
CXC_HOME=$(pwd)

# Go to ckanext-recombinant, identify bona fide target datasets
cd "${BIN_HOME}/../../ckanext-recombinant"
CXR_HOME="$(pwd)"
TARGET_DATASETS=$(paster recombinant target-datasets -c "${INI_PATH}")

# Go to ckanext-canada and fetch resources per target dataset
cd "${CXC_HOME}"
for TARG_DS in $(echo ${TARGET_DATASETS} | tr ' ' '\n')
do
    # Get resource URLs for those datasets specified on command line
    if [ -z "${TARG_DS_MAP[${TARG_DS}]}" ]
    then
        continue
    fi

    CSV_URLS=$(paster canada locate-dataset-resources "${TARG_DS_MAP[${TARG_DS}]}" -c "${INI_PATH}")

    CSV_FILES=""
    for CSV_URL in $(echo ${CSV_URLS} | tr ' ' '\n')
    do
        # Sometimes http://host:port/ is there and sometimes not
        if [[ "${CSV_URL}" =~ :///.* ]]
        then
            CSV_URL=${CSV_URL#*///}
            CSV_URL="http://localhost:${INI_PORT}/${CSV_URL}"
        fi

        # Strip off everything but file name and extension
        FPATH="${TMPDIR}/${CSV_URL#*.*.}"
        CSV_FILES="${CSV_FILES} ${FPATH}"
        wget -q ${CSV_URL} -O "${FPATH}"
        log 'INFO' "Downloaded $(wc -c ${FPATH} | cut -d ' ' -f1) bytes: [${CSV_URL}]"
    done
    CSV_FILES=${CSV_FILES/ /}

    # Rebuild solr core from downloaded .csv files
    paster "${TARG_DS}" clear
    paster "${TARG_DS}" rebuild -f ${CSV_FILES} -c "${INI_PATH}"
    log 'INFO' "Cleared and rebuilt [${TARG_DS}] solr core"
done

# Clean up
/bin/rm -rf "${TMPDIR}"
