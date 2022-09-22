#!/bin/bash

set -e;

function error_message {

    if [[ $1 ]]; then

        printf "\n\033[1;33m${1}\033[0;0m\n\n";
        exit;

    fi

}

function success_message {

    if [[ $1 ]]; then

        printf "\n\033[0;36m\033[1m${1}\033[0;0m\n\n";

    fi

}

config_file=${PORTAL_INI};

if [[ -z "${config_file}" ]]; then

    error_message '[PORTAL_INI|REGISTRY_INI] environment variable not set.';

fi

if [[ -z "$(command -v ckanapi)" ]]; then

    error_message 'ckanapi command not found. Is it accessible in the PATH variable?';

fi

if [[ ! -d "/opt/tbs/tmp" ]]; then

    error_message '/opt/tbs/tmp directory does not exist.';

fi

generated_file='/opt/tbs/wcms/smb/portal/files/ati-informal-requests-analytics.csv';

if [[ ! -f "${generated_file}" ]]; then

    generated_file='/opt/tbs/drupal/smb/portal/files/ati-informal-requests-analytics.csv';

    if [[ ! -f "${generated_file}" ]]; then

        error_message '/opt/tbs/[wcms|drupal]/smb/portal/files/ati-informal-requests-analytics.csv does not exist.';

    fi

fi

tmp_file='/opt/tbs/tmp/ati-informal-requests-analytics.csv';
cp ${generated_file} ${tmp_file};

resource_id='e664cf3d-6cb7-4aaa-adfa-e459c2552e3e';
ckanapi action resource_patch -c ${config_file} id=${resource_id} upload@"${tmp_file}";

if [[ -f "${tmp_file}" ]]; then

    rm -rf ${tmp_file};

fi

success_message 'Done!';
