#!/usr/bin/env python3
"""
Compiles all the reference data for Service Inventory.

All the required files are in the release of
https://github.com/gcperformance/service-data

https://github.com/gcperformance/service-data/blob/master/src/utils.py
    NOTE: program_list compiles fiscal years, orgs, program_ids, and their labels
    NOTE: sid_list compiles fiscal years, orgs, service_ids, and their labels
https://github.com/gcperformance/service-data/blob/master/src/export.py
    NOTE: CSV files in the release use semicolon(;) as the delimiter
"""

import os
import re
import csv
import json
import requests


ORG_LIST_URI = 'https://open.canada.ca/data/api/action/organization_list'
RELEASE_URI = 'https://api.github.com/repos/gcperformance/service-data/releases/latest'

SERVICE_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_service_ids.csv')
SERVICE_ID_HEADERS = ['service_id', 'label_en', 'label_fr', 'org_years']

PROGRAM_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_program_ids.csv')
PROGRAM_ID_HEADERS = ['program_id', 'label_en', 'label_fr', 'org_years']

REQUEST_HEADERS = {'User-Agent': 'CKAN/open-gov/service/gen_ref_data'}

WHITE_SPACE_SUBS = re.compile(r'\xa0|\t|\n|\s+')
TIMESTAMP_MATCH = re.compile(r'^Timestamp:')

ORG_VARIANTS_FILENAME = 'org_var.csv'
PROGRAM_IDS_FILENAME = 'program_list.csv'
SERVICE_IDS_FILENAME = 'sid_list.csv'


def _clean_intake_text(text: str) -> str:
    """
    Normalize special characters and extra spaces
    """
    text = text.replace('\u200b', '')  # zero width char
    text = re.sub(WHITE_SPACE_SUBS, ' ', text)
    return text.strip()


def _generate_data():
    """
    Generate the reference data for Service Inventory

    Gather Program IDs and their English and French names from the directory
    https://api.github.com/repos/gcperformance/service-data/releases/latest/program_list.csv

    Gather Service IDs and their English and French names from
    https://api.github.com/repos/gcperformance/service-data/releases/latest/sid_list.csv

    NOTE: we only start in the 2018-2019 fiscal year as per Policy.

    NOTE: we take the latest Program Names as the ones to use.
    """
    # get available org abbreviations on open gov
    open_orgs = []
    skipped_orgs = set()
    with requests.get(ORG_LIST_URI, stream=True, headers=REQUEST_HEADERS) as response:
        open_orgs = response.json()['result']
    assert open_orgs

    # gather the csv download URIs from the latest release
    org_variants_uri = None
    program_ids_uri = None
    service_ids_uri = None
    with requests.get(RELEASE_URI, stream=False) as response:
        release_assets = response.json()['assets']
        for f in release_assets:
            if f['name'] == ORG_VARIANTS_FILENAME:
                org_variants_uri = f['browser_download_url']
                continue
            if f['name'] == PROGRAM_IDS_FILENAME:
                program_ids_uri = f['browser_download_url']
                continue
            if f['name'] == SERVICE_IDS_FILENAME:
                service_ids_uri = f['browser_download_url']
                continue
    assert org_variants_uri
    assert program_ids_uri
    assert service_ids_uri

    # compile list of Open Canada org abbreviations and Service Inventory org_ids
    org_id_abbr_map = {}
    with requests.get(org_variants_uri, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader(response.iter_lines(decode_unicode=True))

        assert 'org_name_variant' in c.fieldnames
        assert 'org_id' in c.fieldnames

        for row in c:
            oname = _clean_intake_text(row['org_name_variant'])
            if oname in open_orgs:
                org_id_abbr_map[_clean_intake_text(row['org_id'])] = oname
    assert org_id_abbr_map

    # compile map of program_ids
    program_id_map = {}
    with requests.get(program_ids_uri, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader(response.iter_lines(decode_unicode=True),
                           delimiter=';')

        assert 'org_id' in c.fieldnames
        assert 'program_id' in c.fieldnames
        assert 'latest_valid_fy' in c.fieldnames
        assert 'program_en' in c.fieldnames
        assert 'program_fr' in c.fieldnames

        for row in c:
            if not row['program_id']:
                continue
            program_id = _clean_intake_text(row['program_id'])
            if not program_id:
                continue
            if program_id not in program_id_map:
                program_id_map[program_id] = {}

            label_en = _clean_intake_text(row['program_en'])
            label_fr = _clean_intake_text(row['program_fr'])
            if 'label_en' not in program_id_map[program_id]:
                # take first occuring label
                program_id_map[program_id]['label_en'] = label_en
            if 'label_fr' not in program_id_map[program_id]:
                # take first occuring label
                program_id_map[program_id]['label_fr'] = label_fr

            org = _clean_intake_text(row['org_id'])
            if org not in org_id_abbr_map:
                # org not in open gov, skip
                if org not in skipped_orgs:
                    print('Organization %s not available '
                          'in Open Gov Registry. Skipping...' % org)
                    skipped_orgs.add(org)
                continue
            org = org_id_abbr_map[org]

            if 'org_years' not in program_id_map[program_id]:
                program_id_map[program_id]['org_years'] = {}
            if org not in program_id_map[program_id]['org_years']:
                program_id_map[program_id]['org_years'][org] = []
            year = _clean_intake_text(row['latest_valid_fy'])
            if year in program_id_map[program_id]['org_years'][org]:
                continue
            program_id_map[program_id]['org_years'][org].append(year)
    assert program_id_map

    # write program_id ref data
    with open(PROGRAM_ID_OUTPUT_FILE, 'w') as f:
        writer = csv.DictWriter(f, PROGRAM_ID_HEADERS)
        writer.writeheader()
        for program_id, program_data in program_id_map.items():
            writer.writerow({
                'program_id': program_id,
                'label_en': program_data['label_en'],
                'label_fr': program_data['label_fr'],
                'org_years': json.dumps(program_data['org_years'])
                if 'org_years' in program_data else None})

    # write service_id ref data
    inserted_service_ids = set()
    with requests.get(service_ids_uri, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader(response.iter_lines(decode_unicode=True),
                           delimiter=';')

        assert 'service_id' in c.fieldnames
        assert 'service_name_en' in c.fieldnames
        assert 'service_name_fr' in c.fieldnames
        assert 'org_id' in c.fieldnames
        assert 'fiscal_yr_first' in c.fieldnames
        assert 'fiscal_yr_latest' in c.fieldnames

        with open(SERVICE_ID_OUTPUT_FILE, 'w') as f:
            writer = csv.DictWriter(f, SERVICE_ID_HEADERS)
            writer.writeheader()
            for row in c:
                if not row['service_id']:
                    continue
                service_id = _clean_intake_text(row['service_id'])
                if not service_id or re.search(TIMESTAMP_MATCH, service_id):
                    continue
                if service_id in inserted_service_ids:
                    raise Exception('%s already added...' % service_id)

                org = _clean_intake_text(row['org_id'])
                if org not in org_id_abbr_map:
                    # org not in open gov, skip
                    if org not in skipped_orgs:
                        print('Organization %s not available '
                              'in Open Gov Registry. Skipping...' % org)
                        skipped_orgs.add(org)
                    continue
                org = org_id_abbr_map[org]

                inserted_service_ids.add(service_id)

                # just make same format as program_id
                # org_years to make queries the same
                org_years = {}
                org_years[org] = [_clean_intake_text(row['fiscal_yr_latest'])]

                writer.writerow({
                    'service_id': service_id,
                    'label_en': _clean_intake_text(row['service_name_en']),
                    'label_fr': _clean_intake_text(row['service_name_fr']),
                    'org_years': json.dumps(org_years) if org else None})
    assert inserted_service_ids


if __name__ == '__main__':
    _generate_data()
