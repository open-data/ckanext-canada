#!/bin/bash

set -e

function usage() {
    echo "Usage: ${0} CKAN-INI-FILE SOURCE_CKAN_URL \\"
    echo "    TARGET-DATASET:PACKAGE-ID ... [VIRTUAL-ENV-HOME]"
    echo
    echo "This script:"
    echo "- pushes datasets from .csv files to the solr core"
    echo
    echo "e.g., ${0} ../development.ini http://open.canada.ca/vl \\"
    echo "    ati:ati_id pd:pd_id"

    exit -1
}

function log() {
    DT=$(date +'%F %T')
    LEVEL=${1}
    MSG=${2}
    echo ${DT} ${LEVEL} [$(basename "${0}")] ${MSG}
}

LAST_TARG_ARG_IDX=$#
if [ "$#" -lt 3 ]
then
    usage
fi

# Establish bin directory
cd "$(dirname ${0})"
BIN_HOME=$(pwd)

# Set .ini file, get port of operation from [server:main] section
cd "$(dirname ${1})"
INI_FILE=$(basename ${1})
INI_PATH="$(pwd)/${INI_FILE}"

# Where we download csv files
SOURCE_CKAN_URL=${2}

# Associate target datasets with ids
declare -A TARG_DS_MAP
for TARG_ARG in $(seq 3 ${LAST_TARG_ARG_IDX})
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
TARGET_DATASETS=$(ckan -c "${INI_PATH}" recombinant target-datasets)

# Fetch resources per target dataset
cd "${BIN_HOME}"
for TARG_DS in $(echo ${TARGET_DATASETS} | tr ' ' '\n')
do
    # Get resource URLs for those datasets specified on command line
    if [ -z "${TARG_DS_MAP[${TARG_DS}]}" ]
    then
        continue
    fi

    CSV_URLS=$(./resource_urls.py $SOURCE_CKAN_URL "${TARG_DS_MAP[${TARG_DS}]}")

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
	echo "CSV_URL $CSV_URL"
	CSV_TAIL="${CSV_URL##*/}"
        FPATH="${TMPDIR}/${CSV_TAIL#*.*.}"
	echo "FPATH $FPATH"
        CSV_FILES="${CSV_FILES} ${FPATH}"
	echo "CSV_FILES $CSV_FILES"
        ./wget.sh --connect-timeout=10 --read-timeout=30 --dns-timeout=10 -t 20 -w 15 -q ${CSV_URL} -O "${FPATH}"
        log 'INFO' "Downloaded $(wc -c ${FPATH} | cut -d ' ' -f1) bytes: [${CSV_URL}]"
    done
    CSV_FILES=${CSV_FILES/ /}

    # Rebuild solr core from downloaded .csv files
    ckan -c "${INI_PATH}" pd clear "${TARG_DS}"
    ckan -c "${INI_PATH}" pd rebuild "${TARG_DS}" -f ${CSV_FILES}
    log 'INFO' "Cleared and rebuilt [${TARG_DS}] solr core"
done

# Clean up
/bin/rm -rf "${TMPDIR}"
