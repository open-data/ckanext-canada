#!/usr/bin/env python

import ckanapi
import unicodecsv
import requests
import json
import sys
import os.path

OUTPUT_FILE = os.path.join(os.path.split(os.path.abspath(__file__))[0],
    '../ckanext/canada/tables/choices/commodity_code.json')

DATA_SOURCE = 'http://open.canada.ca/data'

GSIN_DATASET = '2ce347e5-02fd-4487-975d-67a435efdf9b'
GSIN_COLUMNS = {'id': 0, 'en':2, 'fr':3}

COMMODITY_DATASET = '92214e02-bb86-433e-81b9-c2a78a518e75'
COMMODITY_COLUMNS = {'id': 9, 'en': 10, 'fr': 11}

choices = {}

def download_csv_filter_output(source, dataset_id, columns):
    """
    Download CSV resource from dataset and print the columns
    """
    ckan = ckanapi.RemoteCKAN(source)
    dataset = ckan.action.package_show(id=dataset_id)
    url = dataset['resources'][0]['url']
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
        if out['id'] in choices:
            sys.stderr.write('duplicate id: %r!\n' % out['id'])
            continue

        choices[out['id']] = {'en': out['en'], 'fr': out['fr']}

download_csv_filter_output(DATA_SOURCE, GSIN_DATASET, GSIN_COLUMNS)
download_csv_filter_output(DATA_SOURCE, COMMODITY_DATASET, COMMODITY_COLUMNS)

json.dump(choices, open(OUTPUT_FILE, 'wb'))
sys.stderr.write('wrote %d items\n' % len(choices))
