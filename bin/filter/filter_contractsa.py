#!/usr/bin/env python3
"filter for contractsa.csv"

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

def main():
    reader = csv.DictReader(sys.stdin)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(sys.stdout, outnames)
    writer.writeheader()
    for row in reader:
        try:
            for rem in REMOVE_COLUMNS:
                del row[rem]
            writer.writerow(row)
        except ValueError:
            pass

main()
