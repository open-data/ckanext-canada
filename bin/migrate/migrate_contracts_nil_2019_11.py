#!/usr/bin/env python

import unicodecsv
import sys
import codecs

FIELDNAMES = 'reporting_period,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

if 'warehouse' in sys.argv and 'user_modified' in in_csv.fieldnames:
    sys.exit(85)

out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

for line in in_csv:
    if 'warehouse' not in sys.argv:
        line['user_modified'] = '*'  # special "we don't know" value

    out_csv.writerow(line)
