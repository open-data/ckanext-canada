#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json
from datetime import datetime, timedelta

from openpyxl.utils.datetime import from_excel

FIELDNAMES = 'ref_number,amendment_number,amendment_date,agreement_type,recipient_type,recipient_business_number,recipient_legal_name,recipient_operating_name,research_organization_name,recipient_country,recipient_province,recipient_city,recipient_postal_code,federal_riding_name_en,federal_riding_name_fr,federal_riding_number,prog_name_en,prog_name_fr,prog_purpose_en,prog_purpose_fr,agreement_title_en,agreement_title_fr,agreement_number,agreement_value,foreign_currency_type,foreign_currency_value,agreement_start_date,agreement_end_date,coverage,description_en,description_fr,naics_identifier,expected_results_en,expected_results_fr,additional_information_en,additional_information_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

def norm_date(d):
    "handle some creative thinking about what constitutes a date"
    d = d.replace('.', '-').strip()
    for fmt in ['%Y-%m-%d', '%b-%d-%Y', '%m/%d/%Y']:
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            pass
    return from_excel(int(d))

def en_bar_fr(en, fr):
    en = (en or fr).replace('|', '/').strip()
    fr = (fr or en).replace('|', '/').strip()
    if en == fr:
        return en
    return en + '|' + fr

try:
    for line in in_csv:
        try:
            if norm_date(line['date']) >= datetime(2018, 4, 1):
                raise ValueError
            if not line['value'].strip():
                raise ValueError
        except ValueError:
            sys.stderr.write('{org} {pid} "{date}"\n'.format(
                date=line['date'],
                pid=line['ref_number'],
                org=line['owner_org']))
            continue

        line['agreement_type'] = line.pop('type').upper()
        line['recipient_legal_name'] = en_bar_fr(
            line.pop('recipient_name_en'),
            line.pop('recipient_name_fr'))
        line['recipient_city'] = en_bar_fr(
            line.pop('recipient_region_en'),
            line.pop('recipient_region_fr'))
        line['prog_purpose_en'] = line.pop('purpose_en')
        line['prog_purpose_fr'] = line.pop('purpose_fr')
        line['agreement_title_en'] = line.pop('proj_name_en')
        line['agreement_title_fr'] = line.pop('proj_name_fr')
        line['agreement_number'] = (
            line.pop('prog_number') + '\t' + line.pop('proj_number')).strip()
        line['agreement_value'] = line.pop('value')
        line['agreement_start_date'] = norm_date(line.pop('date')).strftime('%Y-%m-%d')
        line['additional_information_en'] = (
            line.pop('comments_en') + '\t' + line.pop('additional_info_en')).strip()
        line['additional_information_fr'] = (
            line.pop('comments_fr') + '\t' + line.pop('additional_info_fr')).strip()
        line['amendment_number'] = '0'
        if 'warehouse' in sys.argv[1:]:
            line['user_modified'] = ''  # special "we don't know" value
        else:
            raise KeyError("Invalid value")
        out_csv.writerow(line)

except KeyError:
    sys.exit(85)
