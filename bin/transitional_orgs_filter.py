#!/usr/bin/env python3
# coding=utf-8

"""
throw away all parts of an organization that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump organizations --all -r https://open.canada.ca/data |
    bin/transitional_orgs_filter.py > transitional_orgs.jsonl
"""

import sys
import json
from logging import getLogger


log = getLogger(__name__)

filtered_fields = {'id', 'name', 'title', 'title_translated',
                   'department_number', 'umd_number', 'shortform',
                   'ati_email', 'opengov_email', 'faa_schedule',
                   'registry_access'}

users = '--users' in sys.argv

for stdline in sys.stdin:
    o = json.loads(stdline)
    line = {}
    for key in o:
        if key in filtered_fields:
            line[key] = o[key]

    if users:
        line["users"] = [
            {"name": u["name"], "capacity": u["capacity"]}
            for u in o["users"]]

    try:
        print(json.dumps(line, ensure_ascii=False))
    except Exception as e:
        log.error("Failed on Organization:")
        log.error(line)
        raise Exception(e)
