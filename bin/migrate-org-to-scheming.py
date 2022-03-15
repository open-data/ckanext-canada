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
import re
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
                                     {'all_fields': True,
                                      'include_extras': True})
    for org in orgs:
        # split title in fluent fields
        if org.get('title'):
            title_translated = org[u'title'].split('|')
            org[u'title_translated'] = {u'en': title_translated[0].strip()}
            if len(title_translated) > 1:
                org[u'title_translated'][u'fr'] = title_translated[1].strip()

        # format shortform_fr extra field as shortform fluent field
        if org.get('extras'):
            for extra in org[u'extras']:
                if extra[u'key'] == 'shortform_fr':
                    org[u'shortform'][u'fr'] = extra[u'value']
                    org[u'extras'].pop(org[u'extras'].index(extra))

            if len(org[u'extras']) == 0:
                org.pop('extras')

        if not org[u'shortform'][u'en'] or not org[u'shortform'][u'fr']:
            shortform = org[u'name'].split('-')
            org[u'shortform'][u'en'] = shortform[0]
            org[u'shortform'][u'fr'] = shortform[1] \
                if len(shortform) > 1 else shortform[0]

        # set default ati_email field
        # copied from ckan.logic.validators
        email_pattern = re.compile(
            r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")

        if org.get('ati_email'):
            org[u'ati_email'] = org[u'ati_email'].strip()

        if not org.get('ati_email') or not email_pattern.match(org[u'ati_email']):
            org[u'ati_email'] = 'open-ouvert@tbs-sct.gc.ca'

        output.write(json.dumps(org, ensure_ascii=False))
        output.write('\n')

    output.close()


if __name__ == "__main__":
    main(sys.argv[1:])
