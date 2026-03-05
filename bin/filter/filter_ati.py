#!/usr/bin/env python3

"""
Script that takes csv on stdin with Year, Month as the first two columns
and outputs the header row and all rows within the past two years on stdout
"""

import csv
import sys

from typing import Dict, Any, Optional


START_YEAR_MONTH = 2020, 1  # publicly accessible records

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

BOM = "\N{bom}"


def test(record: Dict[str, Any]) -> Dict[str, Any]:
    return process_row(record)


def process_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter any columns out

    NOTE: csv.DictReader treats every dict value as a string,
          thus we need to do any number and falsy conversion.
          e.g. "0" in a `not` will be False,
               "" in a `not` will be True.
    """
    for rem in REMOVE_COLUMNS:
        if rem in row:
            del row[rem]

    if (int(row['year']), int(row['month'])) >= START_YEAR_MONTH:
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
