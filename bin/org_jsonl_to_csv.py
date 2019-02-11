#!/usr/bin/env python

"""
Script that converts the CKAN organization list generated with

  ckanapi dump organizations --all

Into a simple CSV for publishing on the Open Data Portal
"""

import sys
import csv
import json
import codecs

COLS = [
    'uuid',
    'name_en',
    'name_fr',
    'shortform_en',
    'shortform_fr',
    'department_number',
    'umd_number',
    'open_canada_id',
]

def main():
    sys.stdout.write(codecs.BOM_UTF8)

    writer = csv.DictWriter(sys.stdout, COLS)
    writer.writeheader()

    for line in sys.stdin:
        org = json.loads(line)
        titles = org['title'].encode('utf-8').split(' | ')
        row = {
            'uuid': org['id'].lower(),
            'title_en': titles[0].strip(),
            'title_fr': titles[-1].strip(),
            'open_canada_id': org['name'],
        }
        for e in org['extras']:
            if e['key'] == 'shortform':
                row['short_form_en'] = e['value'].strip()
            if e['key'] == 'shortform_fr':
                row['short_form_fr'] = e['value'].strip()
            elif e['key'] in COLS:
                row[e['key']] = e['value'].strip()

        writer.writerow(row)

main()
