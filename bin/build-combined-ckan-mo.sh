#!/bin/bash

set -e

HERE=`dirname $0`
msgfmt "$HERE/../ckanext/canada/i18n/fr/LC_MESSAGES/ckanext-canada.po" \
    -o "$HERE/../ckanext/canada/i18n/fr/LC_MESSAGES/ckanext-canada.mo"
msgfmt "$HERE/../ckanext/canada/i18n/en/LC_MESSAGES/ckanext-canada.po" \
    -o "$HERE/../ckanext/canada/i18n/en/LC_MESSAGES/ckanext-canada.mo"
