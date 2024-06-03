#!/usr/bin/env python3

import unicodecsv
import sys
import codecs

FIELDNAMES = ['ref_number', 'title_en', 'title_fr', 'description_en', 'description_fr', 'publisher_en', 'publisher_fr', 'date_published', 'language', 'size', 'eligible_for_release', 'program_alignment_architecture_en', 'program_alignment_architecture_fr', 'date_released', 'portal_url_en', 'portal_url_fr', 'user_votes', 'owner_org', 'owner_org_title']

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

try:
    for line in in_csv:
        out_csv.writerow(line)
except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
