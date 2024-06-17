#!/usr/bin/env python3
"filter for travela.csv"

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

# these fields need some kind of value
# or drupal search won't work at all
DRUPAL_SEARCH_HACK = [
    'operational_activities_kdollars',
    'key_stakeholders_kdollars',
    'training_kdollars',
    'other_kdollars',
    'internal_governance_kdollars',
]

def main():
    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        try:
            for rem in REMOVE_COLUMNS:
                try:
                    del row[rem]
                except KeyError:
                    # may be filtering old records that were missing these cols
                    pass
            for hack in DRUPAL_SEARCH_HACK:
                if hack in row and not row[hack]:
                    row[hack] = '.'
            writer.writerow(row)
        except ValueError:
            pass

main()
