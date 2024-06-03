#!/usr/bin/env python3

"""
Script that takes csv on stdin with a publishable column
and outputs the header row and all rows with publishable
= "Y". Columns publishable, record_created, record_modified
and user_modified are removed from output.
"""

import csv
import sys

FILTER_COLUMN = "publishable"
REMOVE_COLUMNS = [
    'publishable',
    'contact_email',
    'high_profile',
    'policy_program_lead_email',
    'rationale',
    'remarks_en',
    'remarks_fr',
    'record_created',
    'record_modified',
    'target_participants_and_audience',
    'user_modified',
]

def main():
    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        try:
            if row[FILTER_COLUMN] == 'Y':
                for rem in REMOVE_COLUMNS:
                    del row[rem]
                # truncate status to remove "closed" reason
                row['status'] = row['status'][:1]
                writer.writerow(row)
        except ValueError:
            pass

main()
