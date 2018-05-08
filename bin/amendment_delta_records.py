#!/usr/bin/env python

import unicodecsv
import sys
import codecs
import sqlite3
import tempfile
import json

AMENDMENT_COLUMN = 'amendment_number'

assert sys.stdin.read(3) == codecs.BOM_UTF8
in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
f0 = in_csv.fieldnames[0]

with tempfile.NamedTemporaryFile() as dbfile:
    conn = sqlite3.connect(dbfile.name)
    c = conn.cursor()

    c.execute('CREATE TABLE records ('
        'owner_org text,'
        'pk text,'
        'amendment integer,'
        'original text,'
        'PRIMARY KEY (owner_org, pk, amendment))')

    for line in in_csv:
        owner_org = line['owner_org']
        pk = line[f0]
        amendment = line[AMENDMENT_COLUMN] or 0
        original = json.dumps(line)

        try:
            c.execute('INSERT INTO records VALUES (?,?,?,?)',
                (owner_org, pk, amendment, original))
        except:
            print (owner_org, pk, amendment, original)
            raise


#out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
#out_csv.writeheader()

