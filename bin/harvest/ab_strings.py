#!/usr/bin/env python3

"""
read json lines alberta metadata on stdin, output strings for translation on stdout
as csv with no header

Strings are taken from fields we translate: title, notes, tags, resource.name
"""


import unicodecsv
import sys
import json

out = unicodecsv.writer(sys.stdout)

seen = set()
def w(t):
    t = t.strip()
    if t and t.lower() not in seen:
        out.writerow([t])
        seen.add(t.lower())

for l in sys.stdin:
    o = json.loads(l)
    w(o['title'])
    w(o['notes'])
    for t in o['tags']:
        w(t['name'])
    for r in o['resources']:
        w(r['name'])
