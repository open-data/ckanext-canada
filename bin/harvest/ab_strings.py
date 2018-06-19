#!/usr/bin/env python

"""
read json lines alberta metadata on stdin, output strings for translation on stdout (one per line)

Strings are taken from fields we translate: title, notes, tags, resource.name
"""


import unicodecsv
import sys
import json

seen = set()
def w(t):
    t = t.strip()
    if t and t.lower() not in seen:
        print t.encode('utf-8')
        seen.add(t.lower())

for l in sys.stdin:
    o = json.loads(l)
    w(o['title'])
    w(o['notes'])
    for t in o['tags']:
        w(t['name'])
    for r in o['resources']:
        w(r['name'])
