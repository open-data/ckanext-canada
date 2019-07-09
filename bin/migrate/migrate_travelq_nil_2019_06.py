#!/usr/bin/env python

import unicodecsv
import sys
import codecs

FIELDNAMES = 'year,month,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()


for line in in_csv:
    q = line.pop('quarter')
    line['user_modified'] = '*'  # special "we don't know" value
    if q == 'Q1':
        line['month'] = 'P3'
        out_csv.writerow(line)
        line['month'] = 'P4'
        out_csv.writerow(line)
        line['month'] = 'P5'
        out_csv.writerow(line)
    elif q == 'Q2':
        line['month'] = 'P6'
        out_csv.writerow(line)
        line['month'] = 'P7'
        out_csv.writerow(line)
        line['month'] = 'P8'
        out_csv.writerow(line)
    elif q == 'Q3':
        line['month'] = 'P9'
        out_csv.writerow(line)
        line['month'] = 'P10'
        out_csv.writerow(line)
        line['month'] = 'P11'
        out_csv.writerow(line)
    elif q == 'Q4':
        line['month'] = 'P12'
        out_csv.writerow(line)
        line['year'] = int(line['year']) + 1
        line['month'] = 'P1'
        out_csv.writerow(line)
        line['month'] = 'P2'
        out_csv.writerow(line)
