#!/usr/bin/env python3
"""
Compiles all the reference data for Service Inventory.

Program Names from the CSV Resources: https://open.canada.ca/data/en/dataset/3c371e57-d487-49fa-bb0d-352ae8dd6e4e
Service ID and Names (and valid Orgs): https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-id-registry.csv
Org Name Variants: https://github.com/gcperformance/utilities/blob/master/goc-service-id-registry.csv
Program IDs for Service IDs (and valid years): https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-program.csv
"""

import sys
import io
import os
import csv
import requests

# TODO: remove stuff:
#           \u200b
#           \xa0 <- whitespace
#           \t and \n
#           all white space to single space

PROGRAM_NAME_PACKAGE_ID = '3c371e57-d487-49fa-bb0d-352ae8dd6e4e'
SERVICE_ID_NAMES_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-id-registry.csv'
ORG_NAME_VARIANTS_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-org-variants.csv'
PROGRAM_ID_SERVICE_ID_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-program.csv'
ORG_LIST_URI = 'https://open.canada.ca/data/api/action/organization_list'

SERVICE_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_service_ids.csv')
SERVICE_ID_HEADERS = ['service_id', 'label_en', 'label_fr']

PROGRAM_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_program_ids.csv')


def _generate_service_id_data():
    """

    """
    with requests.get(SERVICE_ID_NAMES_URI) as response:
        response.encoding = 'utf-8-sig'
        f = io.StringIO(response.text)
        c = csv.DictReader(f)

        assert 'service_id' in c.fieldnames
        assert 'service_en' in c.fieldnames
        assert 'service_fr' in c.fieldnames
        assert 'org_id' in c.fieldnames

    inserted_service_ids = set()
    with open(SERVICE_ID_OUTPUT_FILE, 'w') as f:
        writer = csv.DictWriter(f, SERVICE_ID_HEADERS)
        writer.writeheader()
        for row in c:
            if row['service_id'].strip() in inserted_service_ids:
                raise Exception('%s already added...' % row['service_id'].strip())
            inserted_service_ids.add(row['service_id'].strip())
            writer.writerow({'service_id': row['service_id'].strip(),
                             'label_en': row['service_en'].strip(),
                             'label_fr': row['service_fr'].strip()})


def _generate_data():
    """

    """
    _generate_service_id_data()


if __name__ == '__main__':
    _generate_data()
