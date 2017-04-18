#!/bin/bash
source $HOME/.bashrc

set -e

. /var/www/html/venv/staging-portal/bin/activate

/var/www/html/open_gov/staging-portal/ckanext-canada/bin/csv2solr.sh \
    /var/www/html/open_gov/staging-portal/ckan/production.ini \
    http://open.canada.ca/data \
    ati:0797e893-751e-4695-8229-a5066e4fe43c \
    wrongdoing:6e75f19c-d19d-48aa-984e-609c8d9bc403 \
    travelq:009f9a49-c2d9-4d29-a6d4-1a228da335ce \
    reclassification:f132b8a6-abad-43d6-b6ad-2301e778b1b6 \
    hospitalityq:b9f51ef4-4605-4ef2-8231-62a2edda1b54 \
    grants:432527ab-7aac-45b5-81d6-7597107a7013 \
    contracts:d8f85d91-7dec-4fd1-8055-483b77225d8b \
    travela:4ae27978-0931-49ab-9c17-0b119c0ba92f \
    inventory:4ed351cf-95d8-4c10-97ac-6b3511f359b7

if [ $? -ne 0 ]; then
   /home/odatsrv/bin/sendsentry.sh -t 'rebuild_pd_solr_from_uploaded_csv.sh failed to complete, please investigate' -f /home/odatsrv/run_log/rebuild_pd_solr_from_uploaded_csv.log
fi
