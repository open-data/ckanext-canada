#!/usr/bin/env python3

import sys
import csv
import codecs

assert sys.stdin.read(1) == '\N{BOM}'
sys.stdout.write('\N{BOM}')

reader = csv.DictReader(sys.stdin)
writer = csv.DictWriter(sys.stdout, fieldnames=reader.fieldnames)
writer.writeheader()

try:
    for row in reader:
        row['foreign_currency_value'] = row['foreign_currency_value'].replace('$', '').replace(',','')
        row['agreement_value'] = row['agreement_value'].replace('$', '').replace(',','')
        writer.writerow(row)

except KeyError:
    sys.exit(85)
