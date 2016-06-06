#!/usr/bin/env python

import unicodecsv
import requests
import json
import sys
import os.path

OUTPUT_FILE = os.path.join(os.path.split(__file__)[0],
    '../ckanext/canada/tables/choices/country.json')

DATA_URL = 'https://raw.github.com/datasets/country-codes/master/data/country-codes.csv'

choices = {}

def download_csv_filter_output(url):
    """
    Download CSV and print the columns we need
    """
    response = requests.get(url, stream=True)
    csv = unicodecsv.DictReader(response.iter_lines(), encoding='utf-8')
    for line in csv:
        # skip blanks
        if not line['ISO3166-1-Alpha-2']:
            continue
        if line['ISO3166-1-Alpha-2'] in choices:
            sys.stderr.write('duplicate id: %r!\n' % line['ISO3166-1-Alpha-2'])
            continue
        choices[line['ISO3166-1-Alpha-2']] = {
            'en': line['official_name'],
            'fr': line['official_name_fr']}


download_csv_filter_output(DATA_URL)

json.dump(choices, open(OUTPUT_FILE, 'wb'))
sys.stderr.write('wrote %d items\n' % len(choices))
