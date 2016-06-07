#!/usr/bin/env python

import unicodecsv
import requests
import json
import sys
import os.path

OUTPUT_FILE = os.path.join(os.path.split(__file__)[0],
    '../ckanext/canada/tables/choices/economic_object_code.json')

SOURCE_EN = 'http://www.tpsgc-pwgsc.gc.ca/recgen/pceaf-gwcoa/1617/fichiers-files/rg-7-codes-eng.txt'
SOURCE_FR = 'http://www.tpsgc-pwgsc.gc.ca/recgen/pceaf-gwcoa/1617/fichiers-files/rg-7-codes-fra.txt'


def download_econ(url):
    response = requests.get(url, stream=True)
    csv = unicodecsv.reader(
        response.iter_lines(),
        dialect='excel-tab',
        encoding='utf-8')
    next(csv) # header row
    return dict(csv)
    
fr = download_econ(SOURCE_FR)
en = download_econ(SOURCE_EN)

choices = dict(
    (num, {'en': en[num], 'fr': fr[num]})
    for num in sorted(en))

json.dump(choices, open(OUTPUT_FILE, 'wb'))
sys.stderr.write('wrote %d items\n' % len(en))
