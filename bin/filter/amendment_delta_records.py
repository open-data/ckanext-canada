#!/usr/bin/env python3

import unicodecsv
import sys
import sqlite3
import tempfile
import json

from codecs import BOM_UTF8

assert sys.argv[1] and sys.argv[2], 'usage: amendment_delta_records.py input.csv output.csv'
AMENDMENT_COLUMN = 'amendment_number'
OWNER_ORG = 'owner_org'
OWNER_ORG_TITLE = 'owner_org_title'

def batch_owner_org_pk(c):
    'yield groups of records with the same owner_org and pk values'
    records = c.execute(
        'SELECT * FROM records ORDER BY owner_org, pk, amendment')

    owner_org_pk = None
    batch = []
    for r in records:
        if batch and r[:2] != owner_org_pk:
            yield batch
            batch = []
        owner_org_pk = r[:2]
        batch.append(json.loads(r[3]))
    if batch:
        yield batch


with tempfile.NamedTemporaryFile() as dbfile:
    conn = sqlite3.connect(dbfile.name)
    c = conn.cursor()

    c.execute(
        'CREATE TABLE records ('
        'owner_org text,'
        'pk text,'
        'amendment integer,'
        'original text,'
        'PRIMARY KEY (owner_org, pk, amendment))')

    with open(sys.argv[1], 'rb') as infile:
        assert infile.read(3) == BOM_UTF8  # first 3 bytes, we are in read,bytes mode
        in_csv = unicodecsv.DictReader(infile, encoding='utf-8')
        f0 = in_csv.fieldnames[0]

        for line in in_csv:
            owner_org = line['owner_org']
            pk = line[f0]
            amendment = line[AMENDMENT_COLUMN]
            original = json.dumps(line)

            c.execute('INSERT INTO records VALUES (?,?,?,?)',
                (owner_org, pk, amendment, original))

    with open(sys.argv[2], 'wb') as outfile:
        outfile.write(BOM_UTF8)  # we are in write,bytes mode
        out_csv = unicodecsv.DictWriter(
            outfile, fieldnames=in_csv.fieldnames, encoding='utf-8')
        out_csv.writeheader()

        for batch in batch_owner_org_pk(c):
            if len(batch) == 1:
                row = batch[0]
                row[AMENDMENT_COLUMN] = 'current'
                out_csv.writerow(row)
                continue

            iterator = enumerate(batch)
            i, prev = next(iterator)
            prev[AMENDMENT_COLUMN] = "%02d" % i
            out_csv.writerow(prev)

            for i, row in iterator:
                row[AMENDMENT_COLUMN] = "%02d" % i
                out_csv.writerow({
                    k: v for (k, v) in row.items()
                    if k in (f0, AMENDMENT_COLUMN, OWNER_ORG, OWNER_ORG_TITLE)
                        or v != prev[k]})
                prev = row

            row[AMENDMENT_COLUMN] = 'current'
            out_csv.writerow(row)
