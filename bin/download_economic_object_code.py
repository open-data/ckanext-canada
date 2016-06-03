#!/usr/bin/env python

import unicodecsv
import requests
import json
import sys

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

for num in sorted(en):
    print json.dumps({'id': num, 'en': en[num], 'fr': fr[num]})

sys.stderr.write('wrote %d items\n' % len(en))
