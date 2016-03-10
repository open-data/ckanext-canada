#!/bin/bash

set -e

HERE=`dirname $0`
DEST="$HERE/../build/i18n/fr/LC_MESSAGES/"
mkdir -p $DEST
msgcat --use-first \
    "$HERE/../i18n/fr/LC_MESSAGES/canada.po" \
    "$HERE/../../ckan/ckan/i18n/fr/LC_MESSAGES/ckan.po" \
    "$HERE/../../ckanext-wet-boew/i18n/fr/LC_MESSAGES/wet_boew.po" \
    | msgfmt - -o "$DEST/ckan.mo"

# English overrides
HERE=`dirname $0`
DEST="$HERE/../build/i18n/en/LC_MESSAGES/"
mkdir -p $DEST
msgcat --use-first \
    "$HERE/../i18n/en/LC_MESSAGES/ckan.po" \
    | msgfmt - -o "$DEST/ckan.mo"
