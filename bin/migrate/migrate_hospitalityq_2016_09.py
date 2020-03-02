#!/usr/bin/env python

import unicodecsv
import sys
import codecs

FIELDNAMES = 'ref_number,name,title_en,title_fr,description_en,description_fr,start_date,end_date,employee_attendees,guest_attendees,location_en,location_fr,total,owner_org,owner_org_title'.split(',')

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

sys.stdout.write(codecs.BOM_UTF8)
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        try:
            line['employee_attendees'] = str(int(line.pop('attendees')))
        except ValueError:
            line['employee_attendees'] = '0'
        line['guest_attendees'] = '0'
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
