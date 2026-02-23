#!/usr/bin/env python3

import csv
import os
import sys
import yaml

from typing import Dict, Any


TABLE_YAML = os.path.join(
    os.path.dirname(__file__),
    '../../ckanext/canada/tables/nap6.yaml'
)

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

EXPAND_INDICATORS = [
    'en',
    'fr',
    'deadline_en',
    'deadline_fr',
    'lead_dept',
]

COLUMNS = [
    'reporting_period', 'commitments', 'milestones', 'indicators',
    'indicator_en', 'indicator_fr', 'indicator_deadline_en',
    'indicator_deadline_fr', 'indicator_lead_dept',
    'status', 'progress_en', 'progress_fr', 'evidence_en', 'evidence_fr',
    'challenges', 'challenges_other_en', 'challenges_other_fr', 'owner_org',
    'owner_org_title'
]

BOM = "\N{bom}"


def _get_indicator_choices() -> Dict[str, Any]:
    """
    Returns the choice objects for indicators field schema.
    """
    with open(TABLE_YAML, 'r') as f:
        table = yaml.load(f, yaml.Loader)

    for field in table['resources'][0]['fields']:
        if field['datastore_id'] == 'indicators':
            break
    else:
        raise Exception('indicators field not found in ' + TABLE_YAML)

    # type_ignore_reason: incomplete typing
    return field['choices']  # type: ignore


def test(record: Dict[str, Any]) -> Dict[str, Any]:
    indicators_choices = _get_indicator_choices()
    return process_row(record, indicators_choices)


def process_row(row: Dict[str, Any],
                indicators_choices: Dict[str, Any]) -> Dict[str, Any]:
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

    indicator_choice_obj = indicators_choices[row['indicators']]
    for f in EXPAND_INDICATORS:
        if f.startswith('deadline_'):
            # special case, this one has an en/fr sub-dict
            row['indicator_' + f] = indicator_choice_obj.get('deadline', {}).\
                get(f.split('_')[1], '')
        elif isinstance(indicator_choice_obj.get(f), list):
            row['indicator_' + f] = ','.join(indicator_choice_obj.get(f))
        else:
            row['indicator_' + f] = indicator_choice_obj.get(f, '')

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

    indicators_choices = _get_indicator_choices()

    for row in reader:
        row = process_row(row, indicators_choices)
        writer.writerow(row)


if __name__ == '__main__':
    main()
