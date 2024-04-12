#!/usr/bin/env python3
"generic filter for removing record modified, created fields"

import csv
import sys

REMOVE_COLUMNS = [
    'record_created',
    'record_modified',
    'user_modified',
]

def main():
    reader = csv.DictReader(sys.stdin)
    if not reader.fieldnames:
        # empty file -> empty file for filtering files that did not exist
        return
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
            writer.writerow(row)
        except ValueError:
            pass

main()
