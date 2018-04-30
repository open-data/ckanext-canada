#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json
from datetime import datetime, timedelta

from openpyxl.utils.datetime import from_excel

FIELDNAMES = 'reference_number,procurement_id,vendor_name,contract_date,economic_object_code,description_en,description_fr,contract_period_start,delivery_date,contract_value,original_value,amendment_value,comments_en,comments_fr,additional_comments_en,additional_comments_fr,agreement_type_code,commodity_type_code,commodity_code,country_of_origin,solicitation_procedure_code,limited_tendering_reason_code,exemption_code,aboriginal_business,intellectual_property_code,potential_commercial_exploitation,former_public_servant,standing_offer,standing_offer_number,document_type_code,reporting_period,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

DATE_FORMATS = [
    '%Y-%m-%d',
    '%Y-%m-%d %H:%M:%S',
    '%b-%d-%Y',
    '%m-%d-%Y',
    '%y-%m-%d',
    '%Y/%m/%d',
    '%m/%d/%Y',
    '%d/%m/%Y',
    '%Y %m %d',
    ]

def norm_date(d):
    "handle some creative thinking about what constitutes a date"
    d = d.replace('.', '-').strip()
    if ' [this contract' in d.lower():
        d = d.lower().split(' [this contract')[0]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            pass
    return from_excel(int(d))

for line in in_csv:
    try:
        bad_date = line['contract_date']
        line['contract_date'] = norm_date(line['contract_date'])
        bad_date = line['contract_period_start']
        if bad_date:
            line['contract_period_start'] = norm_date(line['contract_period_start'])
        bad_date = line['delivery_date']
        if bad_date:
            line['delivery_date'] = norm_date(line['delivery_date'])
    except ValueError:
        sys.stderr.write(u'{org} {pid} "{date}"\n'.format(
            date=bad_date,
            pid=line['reference_number'],
            org=line['owner_org']).encode('utf-8'))
        continue

    line['exemption_code'] = line.pop('derogation_code')
    out_csv.writerow(line)
