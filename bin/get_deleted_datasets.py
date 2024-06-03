#!/usr/bin/env python3
# encoding: utf-8
'''
Usage:
    get_deleted_datasets.py <ckan ini file> <xxx.csv>
'''
import json
import os
import sys
import unicodecsv
from unicodecsv import DictReader
import codecs

import configparser
import psycopg2


def write_csv(filename, rows):
    with open(filename, 'wb') as f:
        f.write(codecs.BOM_UTF8)
        writer = unicodecsv.writer(f)
        for r in rows:
            writer.writerow(r)


def read_conf(filename):
    config = configparser.ConfigParser()
    config.read(filename)
    psql_conn_str = config.get('app:main', 'sqlalchemy.url')
    import re
    r = re.match(r'^postgresql://(.*):(.*)@(.*)/(.*)', psql_conn_str)
    return (r.group(1), r.group(2), r.group(3), r.group(4))


def get_deleted_dataset(conf_file):
    user, passwd, host, db = read_conf(conf_file)
    db = db.split('?')[0]
    try:
        conn = psycopg2.connect(
            database=db, user=user,
            password=passwd, host=host, port="5432")
    except:
        import traceback
        traceback.print_exce()
        print("Opened database failed")
        sys.exit(-1)
    cur = conn.cursor()
    cur.execute('''SELECT a.id, b.timestamp,c.value, d.title from package a,
                activity b, package_extra c, public.group d
                where a.state='deleted' and a.id=b.object_id and b.activity_type='deleted package'
                    and a.owner_org=d.id
                    and a.id=c.package_id and c.key='title_translated'; ''')
    rows = cur.fetchall()
    ds = {}
    for row in rows:
        id, ts, title, org = row[0], str(row[1]), row[2], row[3]
        if ds.get(id):
            if ts > ds[id][0]:
                ds[id] = [ts, title, org]
        else:
            ds[id] = [ts, title, org]
    return (zip(ds.keys(), ds.values()))


def dump_dataset(headers, ds, csvfile):
    rows = []
    rows.append(headers)
    for id, [ts, title, org] in ds:
        try:
            title = json.loads(title)
        except:
            title = None
        if title:
            title_en = ([title[k] for k in sorted(title) if k.startswith('en')] + [''])[0]
            title_fr = ([title[k] for k in sorted(title) if k.startswith('fr')] + [''])[0]
            rows.append([title_en, title_fr, org, id, ts])
        else:
            rows.append(['n/a', 'n/a', org, id, ts])
    write_csv(csvfile, rows)


def main():
    ds = get_deleted_dataset(sys.argv[1])
    csvfile = sys.argv[2]
    headers= [u'Title (English) / Titre (anglais)',
              u'Title (French) / Titre (français)',
              u'Organization / Organisation',
              u'Record ID / Identificateur du dossier',
              u'Date and Time Deleted/ Date et heure de suppression'
              ]
    dump_dataset(headers, ds, csvfile)

if __name__=='__main__':
    main()
