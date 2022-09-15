#!/bin/bash

set -e;

#TODO: write error_message function
#TODO: write success_message function

registry_ini=${REGISTRY_INI};

#TODO: remove before deploy...
registry_ini=${REGISTRY_CONFIG};

if [[ -z "${registry_ini}" ]]; then

    error_message='REGISTRY_INI environment variable not set.';
    printf "\n\033[1;33m${error_message}\033[0;0m\n\n";
    exit;

fi

if [[ -z "$(command -v ckanapi)" ]]; then

    error_message='ckanapi command not found. Is it accessible in the PATH variable?';
    printf "\n\033[1;33m${error_message}\033[0;0m\n\n";
    exit;

fi

if [[ ! -d "/opt/tbs/tmp" ]]; then

    error_message='/opt/tbs/tmp directory does not exist.';
    printf "\n\033[1;33m${error_message}\033[0;0m\n\n";
    exit;

fi

remote_file='https://open.canada.ca/sites/default/files/ati-informal-requests-analytics.csv';

#TODO: remove before deploy...
remote_file='http://drupal:8080/sites/default/files/ati-informal-requests-analytics.csv';

tmp_file='/opt/tbs/tmp/ati-informal-requests-analytics.csv';
#wget -O ${tmp_file} ${remote_file};

#TODO: add resource id
# use resource_show locally to do 
# resource_create on the staging and 
# production servers to keep the same id
resource_id=''
#ckanapi action resource_patch -c ${registry_ini} id=${resource_id} upload@"${tmp_file}";

if [[ -f "${tmp_file}" ]]; then

    rm -rf ${tmp_file};

fi

success_message='Done!';
printf "\n\033[0;36m\033[1m${success_message}\033[0;0m\n\n";
