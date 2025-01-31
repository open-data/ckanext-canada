#!/usr/bin/env python
# coding=utf-8

"""
migration script to copy all travelq records
for PCO sub-organizations into PCO organization
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

for line in in_csv:
    if line['owner_org'] in sub_orgs:
        line.update(PCO)
    out_csv.writerow(line)
