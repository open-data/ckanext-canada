#!/bin/bash

HERE=`dirname $0`
msgcat --use-first \
    "$HERE/../i18n/fr/LC_MESSAGES/canada.po" \
    "$HERE/../../ckan/ckan/i18n/fr/LC_MESSAGES/ckan.po" \
    | msgfmt - -o "$HERE/../../ckan/ckan/i18n/fr/LC_MESSAGES/ckan.mo"
