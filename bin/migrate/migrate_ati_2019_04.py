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
    ('DA', ['all disclos', 'in full', 'disclosed entirely', 'fully disclosed',
            'disclosed all', 'communication totale', 'full disclosure',
            'complete', 'publicly available', 'public information', 'all released',
            'disclosed / publi', 'full release', 'disclosed / divulgu',
            'entirely disclosed', 'all dislcose', 'all disclso', 'all diclos',
            'full/complet', 'full /plein', 'all records disclosed',
            'all material public', 'all dislosed', 'documents in public']),
    ('DP', ['in part', 'partial', 'partly', 'partielle']),
    ('EX', ['exempt', 'exemption', 'exempted']),
    ('EC', ['excluded', 'exclusion', 'excluted', 'exclued']),
    ('NE', ['no record', 'not exist', 'not exsist', 'aucun document',
            'no such record', 'no record exist', 'no information',
            'no record located', 'non record exist', 'no related record',
            'no responsive record']),
    ('RT', ['transferred', 'transfered', 'other institution']),
    ('RA', ['abandoned', 'abandonned']),
    ('NC', ['neither confirmed nor den', 'confirm nor den']),
]

skipped = 0
written = 0
skipped_new = 0

for line in in_csv:
    errors = []
    try:
        if not (2007 <= int(line['year']) <= 2019):
            raise ValueError
    except ValueError:
        try:
            line['year'] = line['request_number'].split('-')[1]
            if not (2007 <= int(line['year']) <= 2019):
                raise ValueError
        except (IndexError, ValueError):
            errors.append('invalid year ' + line['year'])

    try:
        if not (1 <= int(float(line['month'])) <= 12):
            raise ValueError
    except ValueError:
        errors.append('invalid month ' + line['month'])
    else:
        line['month'] = '%02f' % int(line['month'])

    if not (
            line['request_number'].strip() or
            len(line['request_number']) > 40 or
            '\r' in line['request_number'] or
            '\n' in line['request_number']):
        errors.append('invalid request_number')
    line['request_number'] = line['request_number'].strip()

    try:
        if not line['pages']:
            line['pages'] = '0'
        if not (0 <= int(line['pages'])):
            raise ValueError
    except ValueError:
        errors.append('invalid pages ' + line['pages'] )

    disp = ' '.join(line['disposition'].lower().split())
    for d, search in DISP_MATCH:
        if any(s in disp for s in search):
            disp = d
            break
    else:

        errors.append('invalid disposition ' + line['disposition'])
    line['disposition'] = disp

    if errors:
        for e in errors:
            sys.stderr.write(
                line['owner_org'] + ' ' +
                json.dumps((line['year'], line['month'], line['request_number'])) +
                '    ' + json.dumps(e) + '\n')
        skipped += 1
        try:
            if int(line['year']) >= 2017:
                skipped_new +=1
        except ValueError:
            pass

    else:
        out_csv.writerow(line)
        written += 1

sys.stderr.write('skipped: {0} written: {1} skipped_new: {2}'.format(skipped, written, skipped_new))
