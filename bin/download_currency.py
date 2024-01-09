#!/usr/bin/env python

import requests
from lxml import etree
import json
import sys
import os.path

OUTPUT_FILE = os.path.join(os.path.split(__file__)[0],
    '../ckanext/canada/tables/choices/currency.json')

DATA_FR_URL = 'https://fr.iban.com/currency-codes.html'
DATA_EN_URL = 'https://iban.com/currency-codes.html'

choices = {}

def extract_currency_name_dict(url):
    """
    return a {symbol: full name} dict from a table at url passed
    """
    response = requests.get(url)
    tree = etree.HTML(response.text)
    out = {}
    for row in tree.xpath('//table/tbody/tr'):
        # e.g. ['AFGHANISTAN ', 'Afghani ', 'APN ', '971 ']
        try:
            country, full_name, symbol, code = row.xpath('./td/text()')
        except ValueError:
            continue
        out[symbol.strip()] = full_name.strip()
    return out

fr_data = extract_currency_name_dict(DATA_FR_URL)
en_data = extract_currency_name_dict(DATA_EN_URL)

combined = {}
for symbol, fr in fr_data.items():
    if symbol not in en_data:
        continue
    combined[symbol] = {'en': en_data[symbol], 'fr': fr}

json.dump(combined, open(OUTPUT_FILE, 'wb'), sort_keys=True, indent=2)
