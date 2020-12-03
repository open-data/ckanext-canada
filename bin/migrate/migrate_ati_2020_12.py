#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

DISP_MATCH = [
    ('DA', ['all disclos', 'full', 'disclosed entirely', #'fully disclosed',
            'disclosed all', 'communication totale', #'full disclosure',
            'complete', 'publicly available', 'public information', 'all released',
            'disclosed / publi', #'full release',
            'disclosed / divulgu',
            'entirely disclosed', 'all dislcose', 'all disclso', 'all diclos',
            #'full/complet', 'full /plein',
            'all records disclosed',
            'all material public', 'all dislosed', 'documents in public',
            'divulgation compl', 'all records releas',
            'all dosclosed', 'divulgation totale']),
    ('DP', ['in part', 'partial', 'partly', 'partielle', 'en partie']),
    ('EX', ['exempt', 'exemption', 'exempted']),
    ('EC', ['excluded', 'exclusion', 'excluted', 'exclued', 'tous exclus']),
    ('NE', ['no record', 'not exist', 'not exsist', 'aucun document',
            'no such record', 'no record exist', 'no information',
            'no record located', 'non record exist', 'no related record',
            'no responsive record', 'inexistant']),
    ('RT', ['transferred', 'transfered', 'other institution', 'other party']),
    ('RA', ['abandoned', 'abandonned']),
    ('NC', ['neither confirmed nor den', 'confirm nor den']),
]

skipped = 0
written = 0
skipped_new = 0

for line in in_csv:
    try:
        line['month'] = '%d' % int(line['month'])
    except ValueError:
        pass

    if not line['pages']:
        line['pages'] = '0'

    disp = ' '.join(line['disposition'].lower().split())
    for d, search in DISP_MATCH:
        if any(s in disp for s in search):
            disp = d
            break
    line['disposition'] = disp

    out_csv.writerow(line)
