#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from openpyxl.utils.datetime import from_excel

FIELDNAMES = 'reference_number,procurement_id,vendor_name,vendor_postal_code,buyer_name,contract_date,economic_object_code,description_en,description_fr,contract_period_start,delivery_date,contract_value,original_value,amendment_value,comments_en,comments_fr,additional_comments_en,additional_comments_fr,agreement_type_code,trade_agreement,land_claims,commodity_type,commodity_code,country_of_origin,solicitation_procedure,limited_tendering_reason,trade_agreement_exceptions,aboriginal_business,aboriginal_business_incidental,intellectual_property,potential_commercial_exploitation,former_public_servant,contracting_entity,standing_offer_number,instrument_type,ministers_office,number_of_bids,article_6_exceptions,award_criteria,socioeconomic_indicator,reporting_period,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()


for line in in_csv:
    line['vendor_postal_code'] = ''
    line['buyer_name'] = ''
    line['contract_value'] = line['contract_value'].replace('$','').replace(',','')
    line['original_value'] = line['original_value'].replace('$','').replace(',','')
    line['amendment_value'] = line['amendment_value'].replace('$','').replace(',','')
    line['trade_agreement'] = ''
    line['land_claims'] = ''
    line['commodity_type'] = line.pop('commodity_type_code')
    line['solicitation_procedure'] = line.pop('solicitation_procedure_code')
    line['limited_tendering_reason'] = line.pop('limited_tendering_reason_code')
    line['trade_agreement_exceptions'] = line.pop('exemption_code')
    line['aboriginal_business_incidental'] = line.pop('aboriginal_business')
    line['aboriginal_business'] = ''
    line['intellectual_property'] = line.pop('intellectual_property_code')
    line['contracting_entity'] = line.pop('standing_offer')
    line['instrument_type'] = line.pop('document_type_code')
    line['number_of_bids'] = ''
    line['article_6_exceptions'] = ''
    line['award_criteria'] = ''
    line['socioeconomic_indicator'] = ''
    line['user_modified'] = '*'  # special "we don't know" value

    # clean up some common mistakes
    if line['contracting_entity'] == 'PSPCSOSA':  # code changed in 2016!
        line['contracting_entity'] = 'PWSOSA'
    if line['contracting_entity'] in ('N/A', 'N', 'NUL'):
        line['contracting_entity'] = ''
    line['country_of_origin'] = line['country_of_origin'].upper().strip()
    if line['country_of_origin'].startswith('CAN'):
        line['country_of_origin'] = 'CA'
    if line['country_of_origin'].startswith('USA'):
        line['country_of_origin'] = 'US'
    line['instrument_type'] = line['instrument_type'].upper().strip()
    line['intellectual_property'] = line['intellectual_property'].upper().strip()
    if ':' in line['intellectual_property']:
        line['intellectual_property'] = line['intellectual_property'].split(':')[0]
    if line['intellectual_property'] == 'N/A':
        line['intellectual_property'] = 'NA'
    line['commodity_type'] = line['commodity_type'].upper().strip()
    if line['commodity_type'].startswith('GOOD'):
        line['commodity_type'] = 'G'
    if line['commodity_type'].startswith('SERVICE'):
        line['commodity_type'] = 'S'
    if ':' in line['commodity_type']:
        line['commodity_type'] = line['commodity_type'].split(':')[0]
    line['solicitation_procedure'] = line['solicitation_procedure'].upper().strip()
    if ':' in line['solicitation_procedure']:
        line['solicitation_procedure'] = line['solicitation_procedure'].split(':')[0]
    if line['solicitation_procedure'].startswith('NON-COMPET'):
        line['solicitation_procedure'] = 'TN'
    if ':' in line['limited_tendering_reason']:
        line['limited_tendering_reason'] = line['limited_tendering_reason'].split(':')[0]

    out_csv.writerow(line)
