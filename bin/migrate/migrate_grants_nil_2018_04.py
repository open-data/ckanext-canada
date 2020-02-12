#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json
from datetime import datetime, timedelta

from openpyxl.utils.datetime import from_excel

FIELDNAMES = 'fiscal_year,quarter,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        y = int(line.pop('year'))
        line['fiscal_year'] = str(y) + '-' + str(y+1)
        if 'warehouse' in sys.argv[1:]:
            line['user_modified'] = ''  # special "we don't know" value
        else:
            raise KeyError("Invalid value")
        out_csv.writerow(line)

except KeyError:
    sys.exit(85)
