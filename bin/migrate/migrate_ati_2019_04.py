#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import json

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
out_csv.writeheader()

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

    disp = line['disposition'].lower()
    if 'all disclosed' in disp or 'disclosed in full' in disp:
        disp = 'DA'
    elif 'in part' in disp:
        disp = 'DP'
    elif 'all exempt' in disp or 'exempted' in disp:
        disp = 'EX'
    elif 'all excluded' in disp:
        disp = 'EC'
    elif 'no records' in disp or 'does not exist':
        disp = 'NE'
    elif 'transferred' in disp:
        disp = 'RT'
    elif 'abandoned' in disp:
        disp = 'RA'
    elif 'neither confirmed nor denied' in disp:
        disp = 'NC'
    else:
        error('invalid disposition ' + line['disposition'])
        continue
    line['disposition'] = disp

    out_csv.writerow(line)
