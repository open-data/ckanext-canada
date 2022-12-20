#!/usr/bin/env python
# coding=utf-8

"""
migration script to copy all briefingt records
for PCO sub-organizations into PCO organization
"""

import unicodecsv
import sys
import codecs


sub_orgs = [ 'ghl-lgc',
             'iga-aig',
             'mdi-mid',
             'miga-maig',
             'dpm-vmp',
             'pkcc-pcprc',
             'ql-lq',
             'srp-rsp',
             ]
PCO = { 'owner_org': 'pco-bcp',
        'owner_org_title': 'Privy Council Office | Bureau du Conseil privé' }

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

for line in in_csv:
    if line['owner_org'] in sub_orgs:
        line['owner_org'] = PCO['owner_org']
        line['owner_org_title'] = PCO['owner_org_title']
    out_csv.writerow(line)
