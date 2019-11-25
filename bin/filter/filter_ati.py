#!/usr/bin/env python2

"""
Script that takes csv on stdin with Year, Month as the first two columns
and outputs the header row and all rows within the past two years on stdout
"""

import datetime
import csv
import sys
import codecs

WINDOW_YEARS = 2

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

def main():
    bom = sys.stdin.read(3)
    if not bom:
        # empty file -> empty file
        return
    assert bom == codecs.BOM_UTF8
    sys.stdout.write(codecs.BOM_UTF8)

    today = datetime.datetime.today()
    start_year_month = (today.year - WINDOW_YEARS, today.month)

    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        try:
            if (int(row['year']), int(row['month'])) >= start_year_month:
                writer.writerow(row)

            for rem in REMOVE_COLUMNS:
                del row[rem]
            writer.writerow(row)
        except ValueError:
            pass

main()
