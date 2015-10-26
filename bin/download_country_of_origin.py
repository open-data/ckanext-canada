#!/usr/bin/env python

import unicodecsv
import requests
import json
import sys

DATA_URL = 'https://raw.github.com/datasets/country-codes/master/data/country-codes.csv'

COUNTRY_COLUMNS = {'id': 2, 'en':0, 'fr':1}

seen_ids = set()

def download_csv_filter_output(url, columns):
    """
    Download CSV and print the columns we need
    """
    response = requests.get(url, stream=True)
    csv = unicodecsv.reader(response.iter_lines(), encoding='utf-8')
    # skip header row
    next(csv)
    for line in csv:
        out = {}
        for k, col_num in columns.iteritems():
            out[k] = line[col_num]
        # skip blanks
        if not out['id']:
            continue
        if out['id'] in seen_ids:
            sys.stderr.write('duplicate id: %r!\n' % out['id'])
            continue
        seen_ids.add(out['id'])
            
        print json.dumps(out)

download_csv_filter_output(DATA_URL, COUNTRY_COLUMNS)

sys.stderr.write('wrote %d items\n' % len(seen_ids))
