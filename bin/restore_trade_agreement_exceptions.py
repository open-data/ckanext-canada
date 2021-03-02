#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json

good = open(sys.argv[1], 'rb')
now = open(sys.argv[2], 'rb')

assert good.read(3) == codecs.BOM_UTF8
assert now.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

good_csv = unicodecsv.DictReader(good, encoding='utf-8')
now_csv = unicodecsv.DictReader(now, encoding='utf-8')
assert good_csv.fieldnames == now_csv.fieldnames

ltr = {}

for row in good_csv:
    ltr[row['owner_org'], row['reference_number']] = row['trade_agreement_exceptions']

fix_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=good_csv.fieldnames, encoding='utf-8')
fix_csv.writeheader()

for row in now_csv:
    try:
        tae = ltr[row['owner_org'], row['reference_number']]
    except KeyError:
        sys.stderr.write('missing: ' + repr((row['owner_org'], row['reference_number'])) + '\n')
        continue
    if tae == row['trade_agreement_exceptions']:
        continue
    row['trade_agreement_exceptions'] = tae
    fix_csv.writerow(row)
