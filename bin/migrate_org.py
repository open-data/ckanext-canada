#!/usr/bin/env python

import psycopg2
import uuid
import sys
from optparse import OptionParser


def main():
    usage = '''usage: %prog [options]
%prog -h for help'''
    parser = OptionParser(usage)
    parser.add_option("-d", "--db", dest="db", help="database name")
    parser.add_option("-u", "--user", dest="user", help="username")
    parser.add_option("-p", "--password", dest="password", help="password")

    (options, args) = parser.parse_args()
    if not options.db or not options.user or not options.password:
        parser.error("must have all the options")
        sys.exit(-1)

    try:
        # conn = psycopg2.connect(database="ckanregistry", user="ckan_default",
        # password="ckan123", host="127.0.0.1", port="5432")
        conn = psycopg2.connect(
            database=options.db, user=options.user,
            password=options.password, host="127.0.0.1", port="5432")
        print "Opened database successfully"
    except:
        print "Opened database failed"
        sys.exit(0)

    cur = conn.cursor()

    '''cur.execute("UPDATE COMPANY set SALARY = 25000.00 where ID=1")
    conn.commit
    print "Total number of rows updated :", cur.rowcount'''

    cur.execute("SELECT id, name, title, state, revision_id  from public.group")
    rows = cur.fetchall()
    orgs = {}
    for row in rows:
        orgs[row[0]] = [row[1], row[2], row[3], row[4]]
        # print "ID = ", row[0], "NAME = ", row[1], 'TITLE= ', row[2]

    c1 = 0
    c2 = 0
    for k, v in orgs.items():
        cur.execute("SELECT id, group_id, key, value, state, revision_id from group_extra " +
            "where key='title_translated' and group_id='%s' and revision_id='%s'" % (k, v[3]))
        rows = cur.fetchall()
        if cur.rowcount > 1:
            raise Exception('error group id: ' + k)
        if cur.rowcount == 1:
            if ' | ' in v[1]:
                raise Exception('not updated group id: ' + k)
            else:
                continue
        print 'TITLE: ', v[1]

        # now update & insertq
        if not (' | ' in v[1]):
            c2 += 1
            title = title_fr = v[1]
        else:
            [title, title_fr] = v[1].split(' | ', 1)
        title = title.replace("'", "''")
        title_fr = title_fr.replace("'", "''")
        translated = "{\"fr\": \"%s\", \"en\": \"%s\"}" % (title_fr, title)
        # cur.execute("UPDATE public.group set title='%s' where id='%s'"%(title,k))
        cur.execute("INSERT INTO group_extra (id, group_id, key, value, state, revision_id) VALUES "
            + "('%s', '%s', 'title_translated','%s','%s','%s')" % (
                str(uuid.uuid4()), k, translated, v[2], v[3]))
        c1 += 1
        conn.commit()

    print "Operation done successfully ", c1, c2
    # print orgs
    conn.close()

if __name__ == "__main__":
    main()
