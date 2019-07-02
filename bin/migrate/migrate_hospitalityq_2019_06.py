#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from datetime import datetime
from decimal import Decimal

from openpyxl.utils.datetime import from_excel


FIELDNAMES = 'ref_number,disclosure_group,title_en,title_fr,name,description_en,description_fr,start_date,end_date,location_en,location_fr,vendor_en,vendor_fr,employee_attendees,guest_attendees,total,additional_comments_en,additional_comments_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

ORG_PREFER_FORMAT = {
    'jus': '%m/%d/%Y',
    'ndcfo-odnfc': '%d/%m/%Y',
    'swc-cfc': '%d/%m/%Y',
}

assert sys.stdin.read(3) == codecs.BOM_UTF8


def norm_date(d, prefer_format):
    "handle some creative thinking about what constitutes a date"
    d = d.replace('.', '-').strip()

    formats = ['%Y-%m-%d', '%b-%d-%Y', '%m/%d/%Y', '%d/%m/%Y', '%B %d %Y', '%B %d %y', '%d %b %y']
    if prefer_format:
        formats.insert(0, prefer_format)

    if not prefer_format:
        try:
            datetime.strptime(d, '%m/%d/%Y')
            datetime.strptime(d, '%d/%m/%Y')
        except ValueError:
            pass
        else:
            raise ValueError

    for fmt in formats:
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            pass
    return from_excel(int(d))


in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

for line in in_csv:
    line['vendor_en'] = ''
    line['vendor_fr'] = ''
    try:
        if line['start_date']:
            line['start_date'] = norm_date(
                line['start_date'],
                ORG_PREFER_FORMAT.get(line['owner_org']))
    except ValueError:
        sys.stderr.write(line['owner_org'] + ' ' + line['ref_number'] + ' start_date ' + line['start_date'] + '\n')
        continue
    try:
        if line['end_date']:
            line['end_date'] = norm_date(
                line['end_date'],
                ORG_PREFER_FORMAT.get(line['owner_org']))
    except ValueError:
        sys.stderr.write(line['owner_org'] + ' ' + line['ref_number'] + 'end_date ' + line['end_date'] + '\n')
        continue
    try:
        if line['total']:
            line['total'] = str(Decimal(line['total']))
    except ValueError:
        sys.stderr.write(line['owner_org'] + ' ' + line['ref_number'] + 'total ' + line['total'] + '\n')
        continue

    line['user_modified'] = '*'  # special "we don't know" value
    out_csv.writerow(line)
