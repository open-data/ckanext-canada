#!/usr/bin/env python
# coding=utf-8

"""
migration script to copy all hospitalityq-nil records
for PCO sub-organizations into PCO organization.
Duplicate records from sub-orgnizations for (year,month)
will be ignored
"""

import codecs
import csv
import sys


sub_orgs = [
    'dpm-vpm',
    'iga-aig',
    'miga-maig',
    'ghl-lgc',
    'mdi-mid',
    'ql-lq',
    'srp-rsp',
    ]

PCO = {
    'owner_org': 'pco-bcp',
    'owner_org_title': 'Privy Council Office | Bureau du Conseil privé',
    }

assert sys.stdin.buffer.read(3) == codecs.BOM_UTF8

in_csv = csv.DictReader(sys.stdin)
out_csv = csv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames)
out_csv.writeheader()

data = []

def report_exists(year, month, owner_org):
    for row in data:
        if row['year'] == year and \
                row['month'] == month and \
                row['owner_org'] == owner_org:
            return True
    return False

for line in in_csv:
    if line['owner_org'] in sub_orgs:
        if not report_exists(line['year'], line['month'], PCO['owner_org']):
            line.update(PCO)
            data.append(line)
    else:
        data.append(line)

for line in data:
    out_csv.writerow(line)
