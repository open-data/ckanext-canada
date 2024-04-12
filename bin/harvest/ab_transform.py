#!/usr/bin/env python3
# coding: UTF-8

"""
Usage: ab_transform.py opendata_ab.jsonl deepldb.csv canada_ab.jsonl

read json lines alberta metadata on from opendata_ab.jsonl, use translations
from deepldb.csv to transform to overwrite canada_ab.jsonl in canada metadata
schema
"""

import codecs
import unicodecsv
import sys
import json

try:
    opendata_ab, deepldb, canada_ab = sys.argv[1:]
except ValueError:
    sys.stderr.write(__doc__)
    sys.exit(1)

header = (
    codecs.BOM_UTF8 + 'source',
    'text',
    'timestamp',
    'detected_source_language',
    'source_lang',
    'target_lang')


xlat = {}
def x(t):
    return xlat[t.lower().strip()]

with open(deepldb) as f:
    reader = unicodecsv.reader(f)
    h = next(reader)
    h = tuple(c.encode('utf-8') for c in h)
    assert h == header, ('wrong header', h, header)
    for src, txt, ts, dsl, sl, tl in reader:
        xlat[src.lower().strip()] = txt

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

SUBJECT = {
    u"arts, Culture and History": u"arts_music_literature",
    u"agriculture": u"agriculture",
    u"economy and finance": u"economics_and_industry",
    u"business and industry": u"economics_and_industry",
    u"education - early childhood to grade 12": u"education_and_training",
    u"education - post - secondary and skills training": u"education_and_training",
    u"education - adult and continuing": u"education_and_training",
    u"government": u"government_and_politics",
    u"interprovincial and international affairs": u"government_and_politics",
    u"health and wellness": u"health_and_safety",
    u"safety and emergency services": u"health_and_safety",
    u"employment and labour": u"labour",
    u"laws and justice": u"law",
    u"environment": u"nature_and_environment",
    u"tourism and parks": u"nature_and_environment",
    u"energy and natural resources": u"nature_and_environment",
    u"persons with disabilities": u"persons",
    u"Aboriginal Peoples": u"persons",
    u"families and children": u"persons",
    u"immigration and migration": u"persons",
    u"seniors": u"persons",
    u"society and communities": u"society_and_culture",
    u"housing and utilities": u"society_and_culture",
    u"population and demography": u"society_and_culture",
    u"sports and recreation": u"society_and_culture",
    u"science, technology and innovation": u"science_and_technology",
    u"roads, driving and transport": u"transport",
}

AUDIENCE = {
    u'aboriginal peoples': u'aboriginal_peoples',
    u'entrepreneur/self-employed': u'business',
    u'children': u'children',
    u'educators': u'educators',
    u'employers': u'employers',
    u'funding applicants': u'funding_applicants',
    u'general public': u'general_public',
    u'artists': u'general_public',
    u'caregivers': u'general_public',
    u'consumers': u'general_public',
    u'employees': u'general_public',
    u'health care professionals': u'general_public',
    u'legal and law enforcement professionals': u'general_public',
    u'lower-income earners': u'general_public',
    u'government': u'government',
    u'immigrants': u'immigrants',
    u'job seekers': u'job_seekers',
    u'media': u'media',
    u'nonprofit/ voluntary organization': u'nongovernmental_organizations',
    u'parents': u'parents',
    u'persons with disabilities': u'persons_with_disabilities',
    u'rural residents': u'rural_community',
    u'farmers': u'rural_community',
    u'seniors': u'seniors',
    u'scientists': u'scientists',
    u'researchers': u'scientists',
    u'students': u'students',
    u'travellers': u'travellers',
    u'visitors to alberta': u'visitors_to_canada',
    u'women': u'women',
    u'youth': u'youth',
}

FREQUENCY = {
    u'Annual': u'P1Y',
    u'Biennial': u'P2Y',
    u'Daily': u'P1D',
    u'Every 2 weeks': u'P2W',
    u'Every 5 years': u'P5Y',
    u'Every 5 Years': u'P5Y',
    u'Irregular': u'irregular',
    u'Monthly': u'P1M',
    u'Once': u'not_planned',
    u'Other': u'unknown',
    u'Quarterly': u'P3M',
    u'Semi-annual': u'P6M',
    u'Weekly': u'P1W',
}

LICENSE_ID = {
    'OGLA': 'ab-ogla',
    'QPTU': 'ab-qptu',
}

RESOURCE_TYPE = {
    None: 'dataset',
    'url': 'dataset',
}

FORMAT = {
    '': 'other',
    '6GB zipped Esri file geodatabase (FGDB)': 'FGDB/GDB',
    'application/vnd.ms-excel (xlsx)': 'XLSX',
    'CSV': 'CSV',
    'DOCX': 'DOCX',
    'ftp': 'other',
    'FTP': 'other',
    'GDB': 'FGDB/GDB',
    'GIF': 'GIF',
    'GML': 'GML',
    'Gridded Data': 'ASCII Grid',
    'HTML': 'HTML',
    'HTTP': 'other',
    'https': 'other',
    'HTTPS': 'other',
    'JSON': 'JSON',
    'KML': 'KML',
    'link': 'other',
    'LINK': 'other',
    'MS Word': 'DOCX',
    'Non-GIS Data': 'other',
    'OData': 'JSON',
    'PDF': 'PDF',
    'SHP': 'SHP',
    'Tabular Data': 'other',
    'TIFF': 'TIFF',
    'WMS': 'WMS',
    '.xls': 'XLS',
    'XLS': 'XLS',
    'XLSX': 'XLSX',
    'XML': 'XML',
    'ZIP': 'ZIP',
}

out = open(canada_ab, 'wb')

for l in open(opendata_ab):
    i = json.loads(l)
    try:
        if any(t['name'].lower() == 'statcan product' for t in i['tags']):
            continue
        out.write((json.dumps({
            'type': 'dataset',
            'collection': 'federated',
            'id': i['id'],
            'name': i['id'],
            'metadata_created': i['metadata_created'],
            'portal_release_date': i['metadata_created'],
            'title_translated': {
                'en': i['title'],
                'fr-t-en': x(i['title'])},
            'org_title_at_publication': {
                'en': i['organization']['title'],
                'fr': ORG_FR[i['organization']['title']]},
            'owner_org': 'ab',
            'maintainer_email': i.get('contact_email') or u'open@gov.ab.ca',
            'notes_translated': {
                'en': i['notes'],
                'fr-t-en': x(i['notes'])},
            'keywords': {
                'en': [tag['name'] for tag in i['tags']],
                'fr-t-en': [x(tag['name']) for tag in i['tags']]},
            'subject': [SUBJECT[t.lower()] for t in i['topic']],
            'audience': [AUDIENCE[a.lower()] for a in i['audience']],
            'jurisdiction': 'provincial',
            'created': i['date_created'],
            'date_modified': i['date_modified'],
            'date_published': i['date_created'],
            'frequency': FREQUENCY[i['updatefrequency']],
            'private': False,
            'program_page_url': {
                'en': 'https://open.alberta.ca/' + i['type'] + '/' + i['name']},
            'license_id': LICENSE_ID[i['license_id']],
            'restrictions': 'unrestricted',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
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
        }, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + u'\n')
            .encode('utf-8'))
    except KeyError as e:
        sys.stderr.write('not found: ' + e.args[0] + '\n')
