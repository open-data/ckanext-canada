#!/usr/bin/env python
r'''
Example usage:

paster recombinant combine ati | ./ati_to_datastore_create.py \
 | ckanapi action datastore_create -i -r http://open.canada.ca/data -a ...
'''

import unicodecsv
import json
import sys

sys.stdin.read(3)
csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')

print json.dumps({
    'resource_id': '19383ca2-b01a-487d-88f7-e1ffbc7d39c2',
    'fields': [
        {'id':'year', 'type':'int'},
        {'id':'month', 'type':'int'},
        {'id':'request_number', 'type':'text'},
        {'id':'summary_en', 'type':'text'},
        {'id':'summary_fr', 'type':'text'},
        {'id':'disposition', 'type':'text'},
        {'id':'pages', 'type':'int'},
        {'id':'owner_org', 'type':'text'},
        {'id':'owner_org_title', 'type':'text'},
    ],
    'primary_key': ['owner_org', 'request_number'],
    'indexes': ['year', 'month'],
    'force': True,
    'records': list(csv),
})
