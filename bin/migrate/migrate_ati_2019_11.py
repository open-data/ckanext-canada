#!/usr/bin/env python

import unicodecsv
import sys
import codecs


FIELDNAMES = 'year,month,request_number,summary_en,summary_fr,disposition,pages,record_created,record_modified,user_modified,umd_number,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()


def error(msg, value=''):
    sys.stderr.write(
        line['owner_org'] + ' ' + line['ref_number'] + ' ' + msg
        + ' ' + unicode(value) + '\n')
    if err_csv:
        err_csv.writerow(original)


for line in in_csv:
    try:
        if line['pages']:
            line['pages'] = str(int(line['pages']))
    except ValueError:
        error('invalid pages', line['pages'])
        continue

    line['user_modified'] = '*'  # special "we don't know" value
    out_csv.writerow(line)
