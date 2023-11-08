#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from decimal import Decimal

FIELDNAMES = 'year,contract_goods_number_of,contracts_goods_original_value,contracts_goods_amendment_value,contract_service_number_of,contracts_service_original_value,contracts_service_amendment_value,contract_construction_number_of,contracts_construction_original_value,contracts_construction_amendment_value,acquisition_card_transactions_number_of,acquisition_card_transactions_total_value,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()


def norm_money(m):
    if '.' not in m and m[-3:-2] == ',' and len(m.split(',')) == 2:
        m = m.replace(',', '.')
    return unicode(Decimal(m))


for line in in_csv:
    line['contract_goods_number_of'] = int(line['contract_goods_number_of'])
    line['contracts_goods_original_value'] = norm_money(line['contracts_goods_original_value'])
    line['contracts_goods_amendment_value'] = norm_money(line['contracts_goods_amendment_value'])
    line['contract_service_number_of'] = int(line['contract_service_number_of'])
    line['contracts_service_original_value'] = norm_money(line['contracts_service_original_value'])
    line['contracts_service_amendment_value'] = norm_money(line['contracts_service_amendment_value'])
    line['contract_construction_number_of'] = int(line['contract_construction_number_of'])
    line['contracts_construction_original_value'] = norm_money(line['contracts_construction_original_value'])
    line['contracts_construction_amendment_value'] = norm_money(line['contracts_construction_amendment_value'])
    line['acquisition_card_transactions_number_of'] = int(line['acquisition_card_transactions_number_of'])
    line['acquisition_card_transactions_total_value'] = norm_money(line['acquisition_card_transactions_total_value'])
    line['user_modified'] = '*'  # special "we don't know" value
    out_csv.writerow(line)
