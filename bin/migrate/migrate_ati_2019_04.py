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
            'full/complet']),
    ('DP', ['in part', 'partial', 'partly', 'partielle']),
    ('EX', ['exempt', 'exemption', 'exempted']),
    ('EC', ['excluded', 'exclusion', 'excluted']),
    ('NE', ['no record', 'not exist', 'not exsist', 'aucun document',
            'no such record', 'no record exist', 'no information',
            'no record located', 'non record exist']),
    ('RT', ['transferred']),
    ('RA', ['abandoned', 'abandonned']),
    ('NC', ['neither confirmed nor den', 'neither confirm nor den']),
]

def error(s):
    sys.stderr.write(
        line['owner_org'] + ' ' +
        json.dumps((line['year'], line['month'], line['request_number'])) + ' ' +
        json.dumps(s) + '\n')

for line in in_csv:
    try:
        if not (2007 <= int(line['year']) <= 2019):
            raise ValueError
    except ValueError:
        try:
            line['year'] = line['request_number'].split('-')[1]
            if not (2007 <= int(line['year']) <= 2019):
                raise ValueError
        except (IndexError, ValueError):
            error('invalid year ' + line['year'] )
            continue

    try:
        if int(line['month']) == 0 or not line['month']:
            line['month'] = '1'
        if not (1 <= int(line['month']) <= 12):
            raise ValueError
    except ValueError:
        error('invalid month ' + line['month'] )
        continue
    line['month'] = '%02f' % int(line['month'])

    if not (
            line['request_number'].strip() or
            len(line['request_number']) > 40 or
            '\r' in line['request_number'] or
            '\n' in line['request_number']):
        error('invalid request_number')
        continue
    line['request_number'] = line['request_number'].strip()

    try:
        if not line['pages']:
            line['pages'] = '0'
        if not (0 <= int(line['pages'])):
            raise ValueError
    except ValueError:
        error('invalid pages ' + line['pages'] )
        continue

    disp = ' '.join(line['disposition'].lower().split())
    for d, search in DISP_MATCH:
        if any(s in disp for s in search):
            disp = d
            break
    else:

        error('invalid disposition ' + line['disposition'])
        continue
    line['disposition'] = disp

    out_csv.writerow(line)
