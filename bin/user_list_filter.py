#!/usr/bin/env python

"""
throw away all parts of an user that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump users --all | ./user_import_filter.py > users.jsonl
"""

import sys
import json

for l in sys.stdin.readlines():
    o = json.loads(l)
    if o["display_name"] == 'visitor':
        continue
    print json.dumps({
        "id": o["id"],
        "display_name": o["display_name"],
        "fullname": o["fullname"],
        "name": o["name"],
        "sysadmin": o["sysadmin"],
        })
