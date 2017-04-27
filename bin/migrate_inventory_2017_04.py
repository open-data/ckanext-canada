#!/usr/bin/env python

import unicodecsv
import sys
import codecs
from datetime import datetime

FIELDNAMES = ['ref_number', 'title_en', 'title_fr', 'description_en', 'description_fr', 'publisher_en', 'publisher_fr', 'date_published', 'language', 'size', 'eligible_for_release', 'program_alignment_architecture_en', 'program_alignment_architecture_fr', 'date_released', 'portal_url_en', 'portal_url_fr', 'user_votes', 'owner_org', 'owner_org_title']

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

def unfunk_date(d):
    if not d:
        return ''
    d = d.strip()
    if len(d) == 4:
        d = d + '-01-01'
    try:
        datetime.strptime(d, '%Y-%m-%d')
        return d
    except ValueError:
        sys.stderr.write((u'bad date: %s\n' % d).encode('utf-8'))
    return ''

for line in in_csv:
    line['date_published'] = unfunk_date(line['date_published'])
    line['date_released'] = unfunk_date(line['date_released'])
    out_csv.writerow(line)
