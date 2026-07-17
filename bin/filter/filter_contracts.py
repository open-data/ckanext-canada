#!/usr/bin/env python3
"filter for contracts.csv"

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]


def main(inf, outf):
    reader = csv.DictReader(inf)
    outnames = [f for f in reader.fieldnames if f not in REMOVE_COLUMNS]
    writer = csv.DictWriter(outf, outnames)
    writer.writeheader()
    for row in reader:
        try:
            for rem in REMOVE_COLUMNS:
                del row[rem]
            writer.writerow(row)
        except ValueError:
            pass


if __name__ == '__main__':
    main(sys.stdin, sys.stdout)
