#!/usr/bin/env python

"""
Usage: ab_transform.py opendata_ab.jsonl deepldb.csv canada_ab.jsonl

read json lines alberta metadata on from opendata_ab.jsonl, use translations
from deepldb.csv to transform to overwrite canada_ab.jsonl in canada metadata
schema
"""

import unicodecsv
import sys
import json

from . import deepl


try:
    opendata_ab, deepldb, canada_ab = sys.argv[1:]
except ValueError:
    sys.stderr.write(__doc__)
    sys.exit(1)

xlat = {}
def x(t):
    return xlat[t.lower()]

with open(deepldb) as f:
    reader = unicodecsv.reader(f)
    h = next(reader)
    h = tuple(c.encode('utf-8') for c in h)
    assert h == deepl.header, ('wrong header', h, header)
    for src, txt, ts, dsl, sl, tl in reader:
        xlat[src.lower()] = txt

ORG_FR = {
    u"Advanced Education": u"Ministère de l'Enseignement postsecondaire",
    u"Agriculture and Forestry": u"Ministère de l'Agriculture et des Forêts",
    u"Alberta Energy Regulator": u"Régulateur de l'énergie de l'Alberta",
    u"Children's Services": u"Ministère des Services à l'enfance",
    u"Communications and Public Engagement": u"Ministères des Communications et de la Mobilisation du public",
    u"Community and Social Services": u"Ministère des Services sociaux et communautaires",
    u"Culture and Tourism": u"Ministère de la Culture et du Tourisme",
    u"Economic Development and Trade": u"Ministère du Développement économique et du Commerce",
    u"Education": u"Ministère de l'Éducation",
    u"Energy": u"Ministère de l'Énergie",
    u"Environment and Parks": u"Ministère de l'Environnement et des Parcs",
    u"Executive Council": u"Conseil exécutif",
    u"Health": u"Ministère de la Santé",
    u"Indigenous Relations": u"Ministère des Relations autochtones",
    u"Infrastructure": u"Ministère de l'Infrastructure",
    u"Justice and Solicitor General": u"Ministère de la Justice et du Solliciteur général",
    u"Labour": u"Ministère du Travail",
    u"Municipal Affairs": u"Ministère des Affaires municipales",
    u"Public Service Commission": u"Commission de la fonction publique",
    u"Seniors and Housing": u"Ministère des Personnes âgées et du Logement",
    u"Service Alberta": u"Ministère de Service Alberta OR Service Alberta",
    u"Status of Women": u"Ministère de la Condition féminine",
    u"Transportation": u"Ministère des Transports",
    u"Treasury Board and Finance": u"Conseil du Trésor et Finances",
}

out = open(canada_ab, 'w')

for l in open(opendata_ab):
    i = json.loads(l)
    json.dump({
        'type': 'dataset',
        'collection': 'alberta',
        'id': i['id'],
        'name': i['id'],
        'metadata_created': i['metadata_created'],
        'portal_release_date': i['metadata_created'],
        'last_updated': i['last_updated'],
        'title_translated': {
            'en': i['title'],
            'fr-t-en': x(i['title'])},
        'org_title_at_publication': {
            'en': i['organization']['title'],
            'fr': ORG_FR[i['organization']['title']]},
        'owner_org': 'ab',
        'maintainer_email': i['maintainer_email'],
        'notes_translated': {
            'en': i['notes'],
            'fr-t-en': x(i['notes'])},
        'tags': {
            'en': [tag['name'] for tag in i['tags']],
            'fr-t-en': [x(tag['name']) for tag in i['tags']]}
        'subject': [SUBJECT[t] for t in i['topic']],
        'audience': [AUDIENCE[a] for a in i['audience']],
        'jurisdiction': 'provincial',
        'created': i['date_created'],
        'date_published': i['date_published'],
        'date_modified': i['date_modified'],
        'frequency': FREQUENCY[i['updatefrequency']],
        'program_page_url': {
            'en': 'https://open.alberta.ca/' + i['type'] + '/' + i['name']}
        'license_id': LICENSE_ID[i['license_id']],
        'resources': [
            {
                'id': r['id'],
                'name_translated': {
                    'en': r['name'],
                    'fr-t-en': x(r['name'])},
                'date_published': r['created'],
                'resource_type': RESOURCE_TYPE[r['resource_type']],
                'format': FORMAT[r['format']],
                'size': r['size'],
                'language': ['en'],
                'url': r['url'],
            } for r in i['resources']
        ]
    }, out)
