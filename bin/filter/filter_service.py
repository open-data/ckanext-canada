#!/usr/bin/env python2

import csv
import sys
import codecs

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

    reader = csv.DictReader(sys.stdin)
    outnames = ['owner_org'] + [f for f in reader.fieldnames
        if f not in REMOVE_COLUMNS and f != 'owner_org']
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
