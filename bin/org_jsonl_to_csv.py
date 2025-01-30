#!/usr/bin/env python3
# coding=utf-8

"""
Script that converts the CKAN organization list generated with

  ckanapi dump organizations --all

Into a simple CSV for publishing on the Open Data Portal
"""

import sys
import csv
import json

COLS = [
    'uuid',
    'title_en',
    'title_fr',
    'short_form_en',
    'short_form_fr',
    'department_number',
    'umd_number',
    'open_canada_id',
]

BOM = '\N{bom}'


def main():
    sys.stdout.write(BOM)

    writer = csv.DictWriter(sys.stdout, COLS)
    writer.writeheader()

    for line in sys.stdin:
        org = json.loads(line)
        row = {
            u'uuid': org[u'id'].lower(),
            u'title_en': org[u'title_translated'][u'en'].strip(),
            u'title_fr': org[u'title_translated'][u'fr'].strip(),
            u'short_form_en': org[u'shortform'][u'en'].strip(),
            u'short_form_fr': org[u'shortform'][u'fr'].strip(),
            u'department_number': org[u'department_number'].strip(),
            u'umd_number': org[u'umd_number'].strip(),
            u'open_canada_id': org[u'name'].strip(),
        }
        writer.writerow(row)


main()
