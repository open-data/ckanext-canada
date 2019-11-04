#!/usr/bin/env python

import unicodecsv
import sys
import codecs


FIELDNAMES = 'year,month,request_number,summary_en,summary_fr,disposition,pages,record_created,record_modified,user_modified,umd_number'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

for line in in_csv:
    line['user_modified'] = '*'  # special "we don't know" value
    out_csv.writerow(line)
