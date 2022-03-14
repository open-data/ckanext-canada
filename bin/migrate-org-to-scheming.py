#!/usr/bin/env python
# coding=utf-8

"""
Generates a JSON lines file which can be used to migrate existing
organizations to use schema defined in organization.yaml

Usage:
migrate-org-to-scheming.py
    -s/--server http://registry.open.canada.ca
    -o/--output outfile.jsonl
"""

import sys
import json
import codecs
import getopt
from ckanapi import RemoteCKAN


def main(argv):
    try:
        server = ''
        outfile = ''
        opts, args = getopt.getopt(argv, "s:o:", ["server=", "output="])
        for opt, arg in opts:
            if opt in ['-s', '--server']:
                server = arg
            if opt in ['-o', '--output']:
                outfile = arg
        if not server or not outfile:
            raise ValueError()

    except Exception:
        print 'USAGE: migrate-org-to-scheming.py ' \
              '-s/--server <remote server> ' \
              '-o/--output outfile.jsonl'
        sys.exit(1)

    output = codecs.open(outfile, 'w', encoding='utf-8')
    ckan_instance = RemoteCKAN(server)
    orgs = ckan_instance.call_action('organization_list',
                                     {'all_fields': True})
    for org in orgs:
        if org.get('title'):
            title_translated = org[u'title'].split(' | ')
            org[u'title_translated'] = {
                u'en': title_translated[0],
                u'fr': title_translated[1]
                if len(title_translated) > 1 else '',
            }
        if org.get('extras') and \
                org[u'extras'][0][u'key'] == 'shortform_fr':
            org[u'shortform']['fr'] = org[u'extras'][0][u'value']
            org.pop('extras')

        output.write(json.dumps(org, ensure_ascii=False))
        output.write('\n')

    output.close()


if __name__ == "__main__":
    main(sys.argv[1:])
