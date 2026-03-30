#!/usr/bin/env python3
"""
Compiles all the reference data for Service Inventory.

Program Names from the CSV Resources: https://open.canada.ca/data/en/dataset/3c371e57-d487-49fa-bb0d-352ae8dd6e4e
Program Names: https://api.github.com/repos/gcperformance/service-data/contents/inputs/backups
Service ID and Names (and valid Orgs): https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-id-registry.csv
Org Name Variants: https://github.com/gcperformance/utilities/blob/master/goc-service-id-registry.csv
Program IDs for Service IDs (and valid years): https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-program.csv
"""

import os
import re
import csv
import requests


PROGRAM_NAME_PACKAGE_ID = '3c371e57-d487-49fa-bb0d-352ae8dd6e4e'
SERVICE_ID_NAMES_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-id-registry.csv'
ORG_NAME_VARIANTS_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-org-variants.csv'
PROGRAM_ID_SERVICE_ID_URI = 'https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-program.csv'
PROGRAM_NAME_DIR_URI = 'https://api.github.com/repos/gcperformance/service-data/contents/inputs/backups'
ORG_LIST_URI = 'https://open.canada.ca/data/api/action/organization_list'

SERVICE_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_service_ids.csv')
SERVICE_ID_HEADERS = ['service_id', 'label_en', 'label_fr', 'org']

PROGRAM_ID_OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/references/data/ref_service_program_ids.csv')
PROGRAM_ID_HEADERS = ['program_id', 'label_en', 'label_fr', 'service_ids', 'org_years']

WHITE_SPACE_SUBS = re.compile(r'\xa0|\t|\n|\s+')
PROGRAM_NAME_EN_FILE_MATCH = re.compile(r'^cp-pc-(.*)-eng\.csv$')
PROGRAM_NAME_FR_FILE_MATCH = re.compile(r'^cp-pc-(.*)-fra\.csv$')

service_id_org_map = {}


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

    Gather Service IDs and their English and French names from
    https://github.com/gcperformance/utilities/raw/refs/heads/master/goc-service-id-registry.csv

    Gather Program IDs and their English and French names from the directory
    https://api.github.com/repos/gcperformance/service-data/contents/inputs/backups

    NOTE: the org_id from the service_id ref data is required
          to properly map Organizations for the program_id ref data.

    NOTE: the Program Name files are separated by English and French, so we
          have to save some objects to memory in this method.

    NOTE: we only start in the 2018-2019 fiscal year as per Policy.

    NOTE: we take the latest Program Names as the ones to use.
    """
    # compile list of Open Canada org abbreviations and Service Inventory org_ids
    org_id_abbr_map = {}
    open_orgs = []
    with requests.get(ORG_LIST_URI, stream=True) as response:
        open_orgs = response.json()['result']
    assert open_orgs
    with requests.get(ORG_NAME_VARIANTS_URI, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader((l.decode('utf-8-sig') for l in response.iter_lines()))

        assert 'org_name_variant' in c.fieldnames
        assert 'org_id' in c.fieldnames

        for row in c:
            oname = _clean_intake_text(row['org_name_variant'])
            if oname in open_orgs:
                org_id_abbr_map[_clean_intake_text(row['org_id'])] = oname

    # get all of the Service IDs
    # NOTE: if a service_id does not have an associated program_id
    #       then we should not use it.
    inserted_service_ids = set()
    service_id_map = {}
    with requests.get(SERVICE_ID_NAMES_URI, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader((l.decode('utf-8-sig') for l in response.iter_lines()))

        assert 'service_id' in c.fieldnames
        assert 'service_en' in c.fieldnames
        assert 'service_fr' in c.fieldnames
        assert 'org_id' in c.fieldnames

        for row in c:
            service_id = _clean_intake_text(row['service_id'])
            if service_id in inserted_service_ids:
                raise Exception('%s already added...' % service_id)
            inserted_service_ids.add(service_id)
            service_id_map[service_id] = {
                'label_en': _clean_intake_text(row['service_en']),
                'label_fr': _clean_intake_text(row['service_fr']),
                'org': org_id_abbr_map[_clean_intake_text(row['org_id'])],
            }
            service_id_org_map[service_id] = org_id_abbr_map[_clean_intake_text(row['org_id'])]

    # get all of the Program Names since 2018-2019 fiscal
    program_id_map = {}
    with requests.get(PROGRAM_NAME_DIR_URI, stream=True) as response:
        tree = response.json()
        for item in tree:
            if item['type'] == 'file':
                english_file = re.search(PROGRAM_NAME_EN_FILE_MATCH, item['name'])
                french_file = re.search(PROGRAM_NAME_FR_FILE_MATCH, item['name'])
                if not english_file and not french_file:
                    continue
                with requests.get(item['download_url'], stream=True) as response:
                    response.encoding = 'utf-8-sig'
                    c = csv.DictReader((l.decode('utf-8-sig') for l in response.iter_lines()))

                    assert 'ProgramInventory-Répertoiredesprogrammes_code_PROG' in c.fieldnames
                    assert 'ProgramInventory_name-Répertoiredesprogrammes_nom_PROG' in c.fieldnames

                    for row in c:
                        program_id = _clean_intake_text(row['ProgramInventory-Répertoiredesprogrammes_code_PROG'])
                        if not program_id:
                            continue
                        if program_id not in program_id_map:
                            program_id_map[program_id] = {}
                        lang_key = None
                        if english_file:
                            lang_key = 'label_en'
                        if french_file:
                            lang_key = 'label_fr'
                        assert lang_key
                        program_id_map[program_id][lang_key] = _clean_intake_text(row['ProgramInventory_name-Répertoiredesprogrammes_nom_PROG'])

    # get the corresponding Service IDs for the Program IDs
    parsed_program_service_ids = set()
    with requests.get(PROGRAM_ID_SERVICE_ID_URI, stream=True) as response:
        response.encoding = 'utf-8-sig'
        c = csv.DictReader((l.decode('utf-8-sig') for l in response.iter_lines()))

        assert 'fiscal_yr' in c.fieldnames
        assert 'service_id' in c.fieldnames
        assert 'program_id' in c.fieldnames

        for row in c:
            program_id = _clean_intake_text(row['program_id'])
            if program_id not in program_id_map:
                raise Exception('%s not found in Program ID list...' % program_id)

            service_id = _clean_intake_text(row['service_id'])
            if service_id not in inserted_service_ids:
                print('WARNING:: service_id does not exist in refernce data: %s' % service_id)
                continue

            parsed_program_service_ids.add(service_id)

            org = service_id_org_map[service_id]

            if 'service_ids' not in program_id_map[program_id]:
                program_id_map[program_id]['service_ids'] = set()

            program_id_map[program_id]['service_ids'].add(_clean_intake_text(row['service_id']))

            if 'org_years' not in program_id_map[program_id]:
                program_id_map[program_id]['org_years'] = set()

            program_id_map[program_id]['org_years'].add((org, _clean_intake_text(row['fiscal_yr'])))

    service_ids_without_programs = inserted_service_ids - parsed_program_service_ids
    with open(SERVICE_ID_OUTPUT_FILE, 'w') as f:
        writer = csv.DictWriter(f, SERVICE_ID_HEADERS)
        writer.writeheader()
        for service_id, service_data in service_id_map.items():
            if service_id in service_ids_without_programs:
                print('WARNING:: service_id does not have any program_ids related to it: %s' % service_id)
                continue
            writer.writerow({'service_id': service_id,
                             'label_en': service_data['label_en'],
                             'label_fr': service_data['label_fr'],
                             'org': service_data['org']})

    with open(PROGRAM_ID_OUTPUT_FILE, 'w') as f:
        writer = csv.DictWriter(f, PROGRAM_ID_HEADERS)
        writer.writeheader()
        for program_id, program_data in program_id_map.items():
            writer.writerow({'program_id': program_id,
                             'label_en': program_data['label_en'],
                             'label_fr': program_data['label_fr'],
                             'service_ids': program_data['service_ids'] if 'service_ids' in program_data else None,
                             'org_years': program_data['org_years'] if 'org_years' in program_data else None,})


if __name__ == '__main__':
    _generate_data()
