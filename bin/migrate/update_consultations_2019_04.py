#!/usr/bin/env python

import unicodecsv
import sys
import codecs

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

for line in in_csv:
    val = line['subjects'].split(',')
    if 'AP' not in val:
        continue
    line['subjects'] = u','.join(
        'IP' if v == 'AP' else v for v in val)
    out_csv.writerow(line)
