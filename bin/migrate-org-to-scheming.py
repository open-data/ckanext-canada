#!/usr/bin/env python3
# coding=utf-8

"""
Generates a JSON lines file which can be used to migrate existing
organizations to use schema defined in organization.yaml

Usage: ckanapi dump organizations --all -c $CONFIG_INI | python
bin/migrate-org-to-scheming.py -o/--output outfile.jsonl """

import sys
import json
import codecs
import getopt


def main(argv):
    try:
        outfile = ''
        opts, args = getopt.getopt(argv, "o:", ["output="])
        for opt, arg in opts:
            if opt in ['-o', '--output']:
                outfile = arg

    except Exception:
        print('Usage: ckanapi dump organizations --all -c $CONFIG_INI | ' \
              'python bin/migrate-org-to-scheming.py -o/--output ' \
              'outfile.jsonl ')
        sys.exit(1)

    output = codecs.open(outfile, 'w', encoding='utf-8')
    for line in sys.stdin.readlines():
        org = json.loads(line)
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
            org[u'shortform'][u'en'] = shortform[0].upper()
            org[u'shortform'][u'fr'] = shortform[1].upper() \
                if len(shortform) > 1 else shortform[0].upper()

        # strip whitespaces from ati_email field
        if org.get('ati_email'):
            org[u'ati_email'] = org[u'ati_email'].strip()

        # set default value as NA for faa_schedule
        org[u'faa_schedule'] = 'NA'

        output.write(json.dumps(org, ensure_ascii=False))
        output.write('\n')

    output.close()


if __name__ == "__main__":
    main(sys.argv[1:])
