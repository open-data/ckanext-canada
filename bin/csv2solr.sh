#!/bin/bash

function usage() {
    echo "Usage: ${0} CKAN-INI-FILE [VIRTUAL-ENV-HOME]"
    echo "The script:"
    echo "- activates virtual environment if specified"
    echo "- pushes datasets from .csv files to the solr core"
    exit -1
}

#
#
# THIS SCRIPT AS IT IS WRITTEN IS HOPELESS: NEEDS TO USE CKANAPI FILE STORAGE
#
#

if [ "$#" -eq 0 ]
then
    usage
elif [ "$#" -gt 1 ]
then
   VENV_HOME=$(echo ${2} | sed -e 's./$..')
   source ${VENV_HOME}/bin/activate
fi

cd "$(dirname ${0})"
BIN_HOME=$(pwd)

# Set ini file
cd "$(dirname ${1})"
INI_FILE=$(basename ${1})
INI_PATH="$(pwd)/${INI_FILE}"

# Record ckanext-canada home
cd "${BIN_HOME}/.."
CXC_HOME=$(pwd)

# Go to ckanext-recombinant
cd "${BIN_HOME}/../../ckanext-recombinant"
CXR_HOME=$(pwd)

# Get target dataset names
TARGET_DATASETS=$(paster recombinant target-datasets -c "${INI_PATH}")
for TARG_DS in $(echo ${TARGET_DATASETS} | tr ' ' '\n')
do
    # Identify .csv files to push to solr
    CSV_FILES=""
    cd "${CXR_HOME}"
    DATASET_TYPES=$(echo $(paster recombinant dataset-types ${TARG_DS} -c "${INI_PATH}") | sed -e 's/.*: //')
    for F in ${DATASET_TYPES}
    do
      CSV_FILES="${CSV_FILES} ${TARG_DS}.${F}.csv"
    done
    CSV_FILES=${CSV_FILES/ /}

    # rebuild solr core from identified .csv files
    cd "${CXC_HOME}"
    paster "${TARG_DS}" rebuild -f ${CSV_FILES} -c "${INI_PATH}" ${TARG_DS}.${DS_TYPE}.csv
done
