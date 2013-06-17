#!/usr/bin/env python

"""
Usage: zcat od_do_canada.jl.gz | convert_dump.py output.xlsx
"""

import sys
import openpyxl
import json

from ckanext.canada.metadata_schema import schema_description

DATASET_FIELDS = [
    ('id', None),
    ('title', lambda d: d['title'] + ' | ' + d.get('title_fra', '')),
#    'notes',
#    'notes_fra',
    ('owner_org', lambda d: d['organization']['title']),
#    'catalog_type',
#    ('subject', lambda d: ', '.join(d['subject'])),
#    'keywords',
#    'keywords_fra',
#    ('geographic_region', lambda d: ', '.join(d['subject'])),
#    'spatial',
#    'spatial_representation_type',
#    'presentation_form',
#    'browse_graphic_url',
    ('date_published', None),
#    'date_modified',
#    'maintenance_and_update_frequency',
]

RESOURCE_FIELDS = [
    ('name', lambda d: d['name'] + ' | ' + d.get('name_fra', '')),
    ('resource_type', None),
    ('url', None),
    ('format', None),
    ('language', None),
]

outname = sys.argv[1]
workbook = openpyxl.Workbook(optimized_write=True)
worksheet = workbook.create_sheet()
worksheet.title = "OD-DO Canada"

worksheet.append([
    ' | '.join(
        schema_description.dataset_field_by_id[i]['label'][lang]
        for lang in schema_description.languages)
    for i, fn in DATASET_FIELDS
    ] + [
    ' | '.join(
        schema_description.resource_field_by_id[i]['label'][lang]
        for lang in schema_description.languages)
    for i, fn in RESOURCE_FIELDS
    ])

for k, jline in enumerate(sys.stdin):
    d = json.loads(jline)
    dataset_info = [fn(d) if fn else d.get(i) for i, fn in DATASET_FIELDS]
    for r in d['resources']:
        worksheet.append(dataset_info + [
            fn(r) if fn else r.get(i) for i, fn in RESOURCE_FIELDS])
        dataset_info = [None] * len(dataset_info)
    if k % 1000 == 0:
        print k

workbook.save(outname)
