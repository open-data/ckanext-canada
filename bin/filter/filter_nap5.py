#!/usr/bin/env python3
"generic filter for removing record modified, created fields"

import os.path
import csv
import sys
import yaml

TABLE_YAML = os.path.join(
    os.path.dirname(__file__),
    '../../ckanext/canada/tables/nap5.yaml'
)

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

COPY_INDICATORS = [
    'en',  # en/fr description
    'fr',
    'due_date',
    'deadline_en',
    'deadline_fr',
    'lead_dept',
    's4d',
]

def main():
    table = yaml.load(open(TABLE_YAML, 'r'))
    for field in table['resources'][0]['fields']:
        if field['datastore_id'] == 'indicators':
            break
    else:
        raise Exception('indicators field not found in ' + TABLE_YAML)
    indicators = field['choices']

    reader = csv.DictReader(sys.stdin)
    if not reader.fieldnames:
        # empty file -> empty file for filtering files that did not exist
        return
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    outnames += ['indicator_' + ind for ind in COPY_INDICATORS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        for rem in REMOVE_COLUMNS:
            del row[rem]

        ind_src = indicators[row['indicators']]
        for ind in COPY_INDICATORS:
            if ind.startswith('deadline_'):
                # special case, this one has an en/fr sub-dict
                row['indicator_' + ind] = ind_src.get('deadline', {}).get(ind.split('_')[1], '').encode('utf-8')
            elif isinstance(ind_src.get(ind), bool):
                row['indicator_' + ind] = 'true' if ind_src.get(ind) else 'false'
            else:
                row['indicator_' + ind] = ind_src.get(ind, '').encode('utf-8')

        writer.writerow(row)

main()
