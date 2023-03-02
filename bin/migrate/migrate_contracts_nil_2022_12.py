#!/usr/bin/env python
# coding=utf-8

"""
migration script to copy all contracts-nil records
for PCO sub-organizations into PCO organization.
Duplicate records from sub-orgnizations for
reporting_period will be ignored
"""

import unicodecsv
import sys
import codecs


sub_orgs = [ 'ghl-lgc',
             'iga-aig',
             'mdi-mid',
             'miga-maig',
             'dpm-vpm',
             'pkcc-pcprc',
             'ql-lq',
             'srp-rsp',
             'nsira-ossnr',
             'ocsec-bccst',
             'snsicp-scpssnr',
             'sirc-csars',
             'jfpc-cfp',
             ]
PCO = { 'owner_org': 'pco-bcp',
        'owner_org_title': 'Privy Council Office | Bureau du Conseil privé' }

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

data = []

def report_exists(reporting_period, owner_org):
    for row in data:
        if row['reporting_period'] == reporting_period and \
                row['owner_org'] == owner_org:
            return True
    return False

for line in in_csv:
    if line['owner_org'] in sub_orgs:
        if not report_exists(line['reporting_period'], PCO['owner_org']):
            line.update(PCO)
            data.append(line)
    else:
        data.append(line)

for line in data:
    out_csv.writerow(line)
