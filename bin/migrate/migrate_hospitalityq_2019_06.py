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
    'cic': '%d/%m/%Y',
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

err_csv = None
original = None
line = None
if sys.argv[1:]:
    err_csv = unicodecsv.DictWriter(
        open(sys.argv[1], 'wb'),
        fieldnames=in_csv.fieldnames,
        encoding='utf-8')
    err_csv.writeheader()

def error(msg, value=''):
    sys.stderr.write(
        line['owner_org'] + ' ' + line['ref_number'] + ' ' + msg
        + ' ' + str(value) + '\n')
    if err_csv:
        err_csv.writerow(original)

try:
    for line in in_csv:
        original = dict(line)

        line['vendor_en'] = ''
        line['vendor_fr'] = ''
        try:
            line['start_date'] = norm_date(
                line['start_date'],
                ORG_PREFER_FORMAT.get(line['owner_org']))
            if line['start_date'] >= datetime(2019, 6, 21):
                error('start_date in the future', line['start_date'])
                continue
        except ValueError:
            error('invalid start_date', line['start_date'])
            continue
        try:
            if line['end_date']:
                line['end_date'] = norm_date(
                    line['end_date'],
                    ORG_PREFER_FORMAT.get(line['owner_org']))
        except ValueError:
            error('invalid end_date', line['end_date'])
            continue
        try:
            if line['guest_attendees']:
                line['guest_attendees'] = str(Decimal(line['guest_attendees']))
                if Decimal(line['guest_attendees']) > 2**31:
                    error('guest_attendees too large', line['guest_attendees'])
                    continue
        except ValueError:
            error('invalid guest_attendees', line['guest_attendees'])
            continue
        try:
            if line['total']:
                line['total'] = str(Decimal(line['total']))
        except ValueError:
            error('invalid total', line['total'])
            continue

        if 'warehouse' not in sys.argv[1:]:
            line['user_modified'] = '*'  # special "we don't know" value

        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
