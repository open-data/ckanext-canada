#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from datetime import datetime
from collections import Counter

from openpyxl.utils.datetime import from_excel


assert sys.stdin.read(3) == codecs.BOM_UTF8

def date_format(d):
    "handle some creative thinking about what constitutes a date"
    d = d.replace('.', '-').strip()
    try:
        datetime.strptime(d, '%m/%d/%Y')
        datetime.strptime(d, '%d/%m/%Y')
    except ValueError:
        pass
    else:
        raise ValueError

    for fmt in ['%Y-%m-%d', '%b-%d-%Y', '%m/%d/%Y', '%d/%m/%Y', '%B %d %Y', '%B %d %y']:
        try:
            datetime.strptime(d, fmt)
            return fmt
        except ValueError:
            pass
    from_excel(int(d))
    return 'excel'


in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

org_counts = Counter()

for line in in_csv:
    try:
        fmt = date_format(line['start_date'])
        org_counts[line['owner_org'], fmt] += 1
    except ValueError:
        pass

    try:
        fmt = date_format(line['end_date'])
        org_counts[line['owner_org'], fmt] += 1
    except ValueError:
        pass

for org, fmt in sorted(org_counts):
    print(org, fmt, org_counts[org, fmt])
