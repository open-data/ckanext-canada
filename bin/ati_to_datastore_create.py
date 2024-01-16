#!/usr/bin/env python
r'''
Example usage:

ckan recombinant combine ati | ./ati_to_datastore_create.py \
 | ckanapi action datastore_create -i -r http://open.canada.ca/data -a ...
'''

import unicodecsv
import json
import sys
import os
import time

import ckanapi
import ckan
from ckanapi.errors import CKANAPIError

proxy= os.environ['http_proxy']

def org_info():
    site = ckanapi.RemoteCKAN('http://registry.open.canada.ca')
    count = 0
    while count <=5:
        try:
            sys.stderr.write('reading organizations...\n')
            orgs = site.action.organization_list(all_fields=True)
            break
        except ckanapi.errors.CKANAPIError:
            count += 1
            print >> sys.stderr, 'Error read org list from open.canada.ca'
            time.sleep(2)
    res = {}
    for rec in orgs:
        count = 0
        while count <=50:
            try:
                print >> sys.stderr, 'read org ' + rec['name']
                org = site.action.organization_show(id=rec['id'])
                break
            except ckanapi.errors.CKANAPIError:
                count += 1
                org = None
                print >> sys.stderr, 'Error read org ' + rec['name']
                time.sleep(2)
        if not org:
            print >> sys.stderr, 'Network error'
            sys.exit(-1)
        extras = org['extras']
        ati_email = None
        for ei in extras:
            if ei['key'] == 'ati_email':
                ati_email = ei['value']
                break
        res[rec['name']] = ati_email
    return res

org_dict = org_info()

sys.stdin.read(3)
csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
csv = list(csv)
for rec in csv:
    title = rec.pop('owner_org_title').split(' | ')
    rec['org_title_en'] = title[0]
    rec['org_title_fr'] = title[1]
    rec['ati_email'] = org_dict.get(rec['owner_org'], '')

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
        {'id':'ati_email', 'type':'text'},
        {'id':'org_title_en', 'type':'text'},
        {'id':'org_title_fr', 'type':'text'},
    ],
    'primary_key': ['owner_org', 'request_number'],
    'indexes': ['year', 'month'],
    'force': True,
    'records': list(csv),
})
