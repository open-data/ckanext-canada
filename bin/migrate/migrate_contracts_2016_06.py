#!/usr/bin/env python3

import unicodecsv
import sys
import codecs

FIELDNAMES = 'unique_identifier,ref_number,vendor_name,contract_date,economic_object_code,description_en,description_fr,contract_period_start,delivery_date,contract_value,original_value,amendment_value,comments_en,comments_fr,additional_comments_en,additional_comments_fr,agreement_type_code,commodity_type_code,commodity_code,country_of_origin,solicitation_procedure_code,limited_tendering_reason_code,derogation_code,aboriginal_business,intellectual_property_code,potential_commercial_exploitation,former_public_servant,standing_offer,standing_offer_number,document_type_code,reporting_period,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
sys.stdout.write(codecs.BOM_UTF8)
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        if not line.get('unique_identifier') or line['unique_identifier'] == 'None':
            line['unique_identifier'] = line['ref_number']
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
