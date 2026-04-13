#!/usr/bin/env python3

"""
Script that takes csv on stdin with a publishable column
and outputs the header row and all rows with publishable
= "Y". Columns publishable, record_created, record_modified
and user_modified are removed from output.
"""

import csv
import sys

from typing import Dict, Any, Optional


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

BOM = "\N{bom}"


def test(record: Dict[str, Any]) -> Dict[str, Any]:
    return process_row(record)


def process_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter any columns out that are not publishable

    NOTE: csv.DictReader treats every dict value as a string,
          thus we need to do any number and falsy conversion.
          e.g. "0" in a `not` will be False,
               "" in a `not` will be True.
    """
    if row[FILTER_COLUMN] == 'Y':
        for rem in REMOVE_COLUMNS:
            if rem in row:
                del row[rem]
        return row

    return None


def main():
    bom = sys.stdin.read(1)  # first code point
    if not bom:
        # empty file -> empty file
        return
    assert bom == BOM
    sys.stdout.write(BOM)

    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        row = process_row(row)
        if row is None:
            continue
        writer.writerow(row)


if __name__ == '__main__':
    main()
