#!/usr/bin/env python

import unicodecsv
import sys
import codecs


FIELDNAMES = 'ref_number,job_number,pos_number,date,pos_title_en,pos_title_fr,old_class_group_code,old_class_level,new_class_group_code,new_class_level,old_differential,new_differential,reason_en,reason_fr,record_created,record_modified,user_modified,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8
sys.stdout.write(codecs.BOM_UTF8)

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        if 'warehouse' not in sys.argv[1:]:
            line['user_modified'] = '*'  # special "we don't know" value
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
