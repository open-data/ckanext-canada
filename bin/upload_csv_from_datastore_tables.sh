#!/bin/bash
source $HOME/.bashrc

set -e

. /var/www/html/venv/rc_reg/bin/activate

REGISTRY_INI="/var/www/html/rc_reg/ckan/production-cli.ini"

BACKUP_DIR="/srv/pd_backup"

TMPDIR=$(mktemp -t -d)

# Export all recombinant tables
cd /var/www/html/rc_reg/ckanext-recombinant
paster recombinant combine -a -d "${TMPDIR}" -c ../ckan/production-cli.ini

# backup
DT="$(date '+%Y%m%d')"
TARGET="$BACKUP_DIR/${DT:0:4}"
mkdir -p "$TARGET" || true
cd "$TMPDIR"
tar czvf "$TARGET/pd-$DT.tar.gz" \
        ati.csv ati-nil.csv \
        contractsa.csv \
        contracts.csv contracts-nil.csv \
	consultations.csv \
        grants.csv grants-nil.csv \
        hospitalityq.csv hospitalityq-nil.csv \
	inventory.csv \
        reclassification.csv reclassification-nil.csv \
        travela.csv \
        travelq.csv travelq-nil.csv \
        wrongdoing.csv

# make inventory csv available pre-filtering
cp inventory.csv /var/www/html/static/inventory.csv
/var/www/html/rc_reg/ckanext-canada/bin/csv2xlsx.py \
	< inventory.csv > /var/www/html/static/inventory.xlsx

# make consultations csv available pre-filtering
cp consultations.csv /var/www/html/static/consultations.csv

# Custom business logic (filtering out records) here
cd /var/www/html/rc_reg/ckanext-canada
mv "${TMPDIR}/ati.csv" "${TMPDIR}/raw-ati.csv"
bin/window_csv_results.py \
        < "${TMPDIR}/raw-ati.csv" \
        > "${TMPDIR}/ati.csv"
mv "${TMPDIR}/ati-nil.csv" "${TMPDIR}/raw-ati-nil.csv"
bin/window_csv_results.py \
        < "${TMPDIR}/raw-ati-nil.csv" \
        > "${TMPDIR}/ati-nil.csv"
mv "${TMPDIR}/inventory.csv" "${TMPDIR}/raw-inventory.csv"
bin/eligible_for_release.py \
        < "${TMPDIR}/raw-inventory.csv" \
        > "${TMPDIR}/inventory.csv"

# UPLOAD
ckanapi action resource_patch -c $REGISTRY_INI \
	id=19383ca2-b01a-487d-88f7-e1ffbc7d39c2 upload@"${TMPDIR}/ati.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=5a1386a5-ba69-4725-8338-2f26004d7382 upload@"${TMPDIR}/ati-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=84a77a58-6bce-4bfb-ad67-bbe452523b14 upload@"${TMPDIR}/wrongdoing.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=8282db2a-878f-475c-af10-ad56aa8fa72c upload@"${TMPDIR}/travelq.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=d3f883ce-4133-48da-bc76-c6b063d257a2 upload@"${TMPDIR}/travelq-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=bdaa5515-3782-4e5c-9d44-c25e032addb7 upload@"${TMPDIR}/reclassification.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=1e955e4d-df35-4441-bf38-b7086192ece2 upload@"${TMPDIR}/reclassification-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=7b301f1a-2a7a-48bd-9ea9-e0ac4a5313ed upload@"${TMPDIR}/hospitalityq.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=36a3b6cc-4f45-4081-8dbd-2340ca487041 upload@"${TMPDIR}/hospitalityq-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=1d15a62f-5656-49ad-8c88-f40ce689d831 upload@"${TMPDIR}/grants.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=4e4db232-f5e8-43c7-b8b2-439eb7d55475 upload@"${TMPDIR}/grants-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=fac950c0-00d5-4ec1-a4d3-9cbebf98a305 upload@"${TMPDIR}/contracts.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=fa4ff6c4-e9af-4491-9d4e-2b468e415a68 upload@"${TMPDIR}/contracts-nil.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=d0df95a8-31a9-46c9-853b-6952819ec7b4 upload@"${TMPDIR}/inventory.csv"
ckanapi action resource_patch -c $REGISTRY_INI \
	id=a811cac0-2a2a-4440-8a81-2994fc753171 upload@"${TMPDIR}/travela.csv"

# clean up
rm "${TMPDIR}"/*.csv
rmdir "${TMPDIR}"
