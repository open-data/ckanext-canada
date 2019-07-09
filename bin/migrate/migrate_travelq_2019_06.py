#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from datetime import datetime
from decimal import Decimal, InvalidOperation

from openpyxl.utils.datetime import from_excel


FIELDNAMES = 'ref_number,disclosure_group,title_en,title_fr,name,purpose_en,purpose_fr,start_date,end_date,destination_en,destination_fr,airfare,other_transport,lodging,meals,other_expenses,total,additional_comments_en,additional_comments_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

ORG_PREFER_FORMAT = {
    'cic': '%d/%m/%Y',
    'jus': '%m/%d/%Y',
    'vrab-tacra': '%d/%m/%Y',
    'dnd-mdn': '%d/%m/%Y',
}

assert sys.stdin.read(3) == codecs.BOM_UTF8


def norm_date(d, prefer_format):
    "handle some creative thinking about what constitutes a date"
    d = d.replace('.', '-').strip()

    formats = [
        '%Y-%m-%d', '%b-%d-%Y', '%m/%d/%Y', '%d/%m/%Y', '%B %d %Y', '%B %d %y', '%d %b %y', '%Y/%m/%d',
        '%d %B, %y', '%d %b-%y', '%d %B-%y', '%d %B, %Y', '%d-%b-%y', '%B %d %Y', '%d / %m / %Y', '%d//%m/%Y']
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

def error(msg, value=None):
    sys.stderr.write(
        line['owner_org'] + ' ' + line['ref_number'] + ' ' + msg
        + ' ' + unicode(value) + '\n')
    if err_csv:
        err_csv.writerow(original)


for line in in_csv:
    original = dict(line)

    if not line['ref_number'].strip():
        error('missing ref_number')
        continue

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

    # fix cic shifted columns
    if line['owner_org'] == 'cic':
        try:
            Decimal(line['additional_comments_en'])
            Decimal(line['additional_comments_fr'])
            try:
                Decimal(line['airfare'])
            except (ValueError, InvalidOperation):
                pass
            else:
                raise ValueError
            try:
                Decimal(line['other_transport'])
            except (ValueError, InvalidOperation):
                pass
            else:
                raise ValueError
        except (ValueError, InvalidOperation):
            pass
        else:
            c1 = line['airfare']
            c2 = line['other_transport']
            c3 = line['accomodation']
            c4 = line['meals']
            c5 = line['other_expenses']
            c6 = line['total']
            c7 = line['additional_comments_en']
            c8 = line['additional_comments_fr']
            line['airfare'] = c3
            line['other_transport'] = c4
            line['accomodation'] = c5
            line['meals'] = c6
            line['other_expenses'] = c7
            line['total'] = c8
            line['additional_comments_en'] = c1
            line['additional_comments_fr'] = c2

    line['lodging'] = line.pop('accomodation')

    for f in 'airfare', 'other_transport', 'lodging', 'meals', 'other_expenses', 'total':
        try:
            if line[f]:
                line[f] = str(Decimal(line[f]))
        except (ValueError, InvalidOperation):
            error(f, line[f])
            break
    else:
        line['user_modified'] = '*'  # special "we don't know" value
        out_csv.writerow(line)
