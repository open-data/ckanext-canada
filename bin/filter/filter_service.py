#!/usr/bin/env python3

import csv
import os
import sys
import yaml


REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

BOM = "\N{bom}"
PROGRAM_NAMES_FILE = os.path.join(os.path.split(__file__)[0],
                           '../../ckanext/canada/tables/choices/service_program_names.yaml')

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
        for rem in REMOVE_COLUMNS:
            del row[rem]

        # calculate total number of applications
        row['num_applications_total'] = 0
        num_fields = [ 'num_applications_by_phone',
                       'num_applications_online',
                       'num_applications_in_person',
                       'num_applications_by_mail',
                       'num_applications_by_email',
                       'num_applications_by_fax',
                       'num_applications_by_other',
                       ]
        for field in num_fields:
            if row[field] in ['NA', 'ND']:
                count = 0
            else:
                count = int(row[field])
            row['num_applications_total'] += count

        # populate program names from ids
        row['program_name_en'] = []
        row['program_name_fr'] = []
        program_ids = row['program_id'].split(',')
        with open(PROGRAM_NAMES_FILE, 'r') as file:
            program_names = yaml.safe_load(file)

        for id in program_ids:
            if id in program_names:
                row['program_name_en'].append(program_names[id]['en'])
                row['program_name_fr'].append(program_names[id]['fr'])

        row['program_name_en'] = str(row['program_name_en'])[1:-1]
        row['program_name_fr'] = str(row['program_name_fr'])[1:-1]

        writer.writerow(row)

main()
