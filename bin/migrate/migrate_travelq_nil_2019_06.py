#!/usr/bin/env python

import unicodecsv
import sys
import codecs

FIELDNAMES = 'year,month,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        q = line.pop('quarter')
        if 'warehouse' in sys.argv[1:]:
            line['user_modified'] = ''  # special "we don't know" value
        else:
            raise KeyError("Invalid value")
        if q == 'Q1':
            line['month'] = 'P01'
            out_csv.writerow(line)
            line['month'] = 'P02'
            out_csv.writerow(line)
            line['year'] = int(line['year']) - 1
            line['month'] = 'P12'
            out_csv.writerow(line)
        elif q == 'Q2':
            line['month'] = 'P03'
            out_csv.writerow(line)
            line['month'] = 'P04'
            out_csv.writerow(line)
            line['month'] = 'P05'
            out_csv.writerow(line)
        elif q == 'Q3':
            line['month'] = 'P06'
            out_csv.writerow(line)
            line['month'] = 'P07'
            out_csv.writerow(line)
            line['month'] = 'P08'
            out_csv.writerow(line)
        elif q == 'Q4':
            line['month'] = 'P09'
            out_csv.writerow(line)
            line['month'] = 'P10'
            out_csv.writerow(line)
            line['month'] = 'P11'
            out_csv.writerow(line)

except KeyError:
    sys.exit(85)
