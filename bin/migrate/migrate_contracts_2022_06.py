#!/usr/bin/env python3

import sys
import csv
import codecs

assert sys.stdin.read(3) == codecs.BOM_UTF8

RENAME_COLUMNS = {
    'aboriginal_business': 'indigenous_business',
    'aboriginal_business_incidental': 'indigenous_business_excluding_psib',
}

reader = csv.DictReader(sys.stdin)
writer = csv.DictWriter(
    sys.stdout,
    fieldnames=list(
        RENAME_COLUMNS.get(name, name) for name in reader.fieldnames),
)
writer.writeheader()

try:
    for row in reader:
        for old, new in RENAME_COLUMNS.items():
            row[new] = row.pop(old)
        writer.writerow(row)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
