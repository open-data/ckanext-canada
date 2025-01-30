#!/usr/bin/env python3

"""
throw away all parts of an user that we don't want to propagate
to another ckan instance.

Usage:

ckanapi dump users --all | ./user_import_filter.py > users.jsonl
"""

import sys
import json

for line in sys.stdin.readlines():
    o = json.loads(line)
    if o["display_name"] == 'visitor':
        continue
    print(json.dumps({
        "id": o["id"],
        "apikey": o["apikey"],
        "display_name": o["display_name"],
        "email": o["email"],
        "fullname": o["fullname"],
        "name": o["name"],
        "password_hash": o["password_hash"],
        "sysadmin": o["sysadmin"],
        }))
