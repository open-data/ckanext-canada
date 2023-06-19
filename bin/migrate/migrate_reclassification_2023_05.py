#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from datetime import datetime

from openpyxl.utils.datetime import from_excel

FIELDNAMES = 'ref_number,job_number,pos_number,date,pos_title_en,pos_title_fr,old_class_group_code,old_class_level,new_class_group_code,new_class_level,old_differential,new_differential,reason_en,reason_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8


in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        original = dict(line)

        line['old_class_group_code'] = line['old_class_group_code'].strip()
        line['new_class_group_code'] = line['new_class_group_code'].strip()

        if line['old_class_group_code'] == 'MG':
            line['old_class_group_code'] = 'MG-SPS'
        if line['new_class_group_code'] == 'MG':
            line['new_class_group_code'] = 'MG-SPS'

        if not line['pos_title_en']:
            line['pos_title_en'] = 'NA'
        if not line['pos_title_fr']:
            line['pos_title_fr'] = 'S.O.'
        if not line['reason_en']:
            line['reason_en'] = 'NA'
        if not line['reason_fr']:
            line['reason_fr'] = 'S.O.'

        if 'warehouse' not in sys.argv[1:]:
            line['user_modified'] = '*'  # special "we don't know" value
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
