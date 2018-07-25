#!/usr/bin/env python

"""
throw away all parts of an organization that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump organizations --all -r http://registry.data.gc.ca | bin/transitional_orgs_filter.py > transitional_orgs.jsonl
"""

import sys
import json

EXTRAS = set([
    'department_number',
    'umd_number',
    'shortform',
    'shortform_fr',
    'ati_email',
    'opengov_email',
    ])

users = '--users' in sys.argv

for l in sys.stdin:
    o = json.loads(l)
    old_extras = dict((e['key'], e['value']) for e in o['extras'])
    line = {
        "title": o["title"],
        "id": o["id"],
        "extras": [{"value": old_extras.get(ename, ''), "key": ename}
            for ename in EXTRAS],
        "name": o["name"],
        }
    if users:
        line["users"] = [
            {"name": u["name"], "capacity": u["capacity"]}
            for u in o["users"]]

    print json.dumps(line)

