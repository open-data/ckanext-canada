#!/usr/bin/env python3

import csv
import os
import sys

from typing import Dict, Any


REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

COLUMNS = [
    'fiscal_yr', 'service_id', 'service_name_en', 'service_name_fr',
    'service_description_en', 'service_description_fr',
    'service_type', 'service_recipient_type', 'service_scope',
    'client_target_groups',
    'program_id', 'program_name_en', 'program_name_fr',
    'client_feedback_channel',
    'automated_decision_system', 'automated_decision_system_description_en',
    'automated_decision_system_description_fr', 'service_fee',
    'os_account_registration', 'os_authentication', 'os_application',
    'os_decision', 'os_issuance', 'os_issue_resolution_feedback',
    'os_comments_client_interaction_en', 'os_comments_client_interaction_fr',
    'last_service_review', 'last_service_improvement', 'sin_usage',
    'cra_bn_identifier_usage', 'num_phone_enquiries', 'num_applications_by_phone',
    'num_website_visits', 'num_applications_online', 'num_applications_in_person',
    'num_applications_by_mail', 'num_applications_by_email',
    'num_applications_by_fax', 'num_applications_by_other', 'num_applications_total',
    'special_remarks_en', 'special_remarks_fr', 'service_uri_en', 'service_uri_fr',
    'owner_org', 'owner_org_title',
]

BOM = "\N{bom}"

SERVICE_ID_REF_DATA_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../../ckanext/canada/tables/references'
    '/data/ref_service_service_ids.csv')
SERVICE_IDS = {}
with open(SERVICE_ID_REF_DATA_FILE, 'r') as f:
    c = csv.DictReader(f)
    for row in c:
        SERVICE_IDS[c['service_id']] = {
            'en': c['label_en'],
            'fr': c['label_fr']
        }

PROGRAM_ID_REF_DATA_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../../ckanext/canada/tables/references'
    '/data/ref_service_program_ids.csv')
PROGRAM_IDS = {}
with open(PROGRAM_ID_REF_DATA_FILE, 'r') as f:
    c = csv.DictReader(f)
    for row in c:
        PROGRAM_IDS[c['program_id']] = {
            'en': c['label_en'],
            'fr': c['label_fr']
        }


def test(record: Dict[str, Any]) -> Dict[str, Any]:
    return process_row(record)


def process_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add dynamic, calculated fields to the row.

    NOTE: csv.DictReader treats every dict value as a string,
          thus we need to do any number and falsy conversion.
          e.g. "0" in a `not` will be False,
               "" in a `not` will be True.
    """
    for rem in REMOVE_COLUMNS:
        if rem in row:
            del row[rem]

    # calculate total number of applications
    row['num_applications_total'] = 0
    num_fields = ['num_applications_by_phone',
                  'num_applications_online',
                  'num_applications_in_person',
                  'num_applications_by_mail',
                  'num_applications_by_email',
                  'num_applications_by_fax',
                  'num_applications_by_other',]
    for field in num_fields:
        if row[field] in ['NA', 'ND']:
            count = 0
        else:
            count = int(row[field])
        row['num_applications_total'] += count

    # populate service names from ids
    row['service_name_en'] = SERVICE_IDS[row['service_id']]['en']
    row['service_name_fr'] = SERVICE_IDS[row['service_id']]['fr']

    # populate program names from ids
    row['program_name_en'] = []
    row['program_name_fr'] = []
    program_ids = row['program_id'].split(',')
    for id in program_ids:
        if id not in PROGRAM_IDS:
            continue
        # NOTE: we add double quotes as Program Names can have
        #       single quotes and commas in them
        row['program_name_en'].append('"%s"' % PROGRAM_IDS[id]['en'])
        row['program_name_fr'].append('"%s"' % PROGRAM_IDS[id]['fr'])

    row['program_name_en'] = ', '.join(row['program_name_en'])
    row['program_name_fr'] = ', '.join(row['program_name_fr'])

    return row


def main():
    bom = sys.stdin.read(1)  # first code point
    if not bom:
        # empty file -> empty file
        return
    assert bom == BOM
    sys.stdout.write(BOM)

    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, COLUMNS)
    writer.writeheader()

    for row in reader:
        row = process_row(row)
        writer.writerow(row)


if __name__ == '__main__':
    main()
