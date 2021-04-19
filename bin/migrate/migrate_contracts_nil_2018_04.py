#!/usr/bin/env python

import unicodecsv
import sys
import codecs

FIELDNAMES = ['reporting_period', 'owner_org', 'owner_org_title']

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        year = int(line.pop('year'))
        quarter = line.pop('quarter')
        line['reporting_period'] = "%04d-%04d-%s" % (
            year,
            year + 1,
            quarter)
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
