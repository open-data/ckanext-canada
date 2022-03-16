#!/usr/bin/env python
# coding=utf-8

"""
throw away all parts of an organization that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump organizations --all -r http://registry.data.gc.ca | bin/transitional_orgs_filter.py > transitional_orgs.jsonl
"""

import sys
import json

filtered_fields = {u'id', u'name', u'title', u'title_translated',
                   u'department_number', u'umd_number', u'shortform',
                   u'ati_email', u'opengov_email'}

users = '--users' in sys.argv

for l in sys.stdin:
    o = json.loads(l)
    line = {}
    for key in o:
        if key in filtered_fields:
            line[key] = o[key]

    if users:
        line["users"] = [
            {"name": u["name"], "capacity": u["capacity"]}
            for u in o["users"]]

    print json.dumps(line, ensure_ascii=False).encode('utf-8')
