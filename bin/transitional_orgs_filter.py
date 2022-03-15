#!/usr/bin/env python

"""
throw away all parts of an organization that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump organizations --all -r http://registry.data.gc.ca | bin/transitional_orgs_filter.py > transitional_orgs.jsonl
"""

import sys
import json

filtered_fields = {'id', 'name', 'title', 'title_translated',
                   'department_number', 'umd_number', 'shortform',
                   'ati_email', 'opengov_email'}

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

    print json.dumps(line)
