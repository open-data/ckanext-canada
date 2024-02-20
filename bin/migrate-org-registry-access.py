#!/usr/bin/env python
# coding=utf-8

"""
Migrate existing organizations to add default value for
registry_access field in schema defined in organization.yaml

Usage: ckanapi dump organizations --all -c $CONFIG_INI | python
migrate-org-registry-access.py --output outfile.jsonl """

import sys
import json
import codecs
import getopt


def main(argv):
    try:
        outfile = ''
        opts, args = getopt.getopt(argv, "o:", ["output="])
        for opt, arg in opts:
            if opt == '--output':
                outfile = arg

    except Exception:
        print('Usage: ckanapi dump organizations --all -c $CONFIG_INI | ' \
              'python migrate-org-registry-access.py --output outfile.jsonl')
        sys.exit(1)

    output = codecs.open(outfile, 'w', encoding='utf-8')

    for line in sys.stdin.readlines():
        org = json.loads(line)
        # default to 'internal'
        org[u'registry_access'] = 'internal'

        output.write(json.dumps(org, ensure_ascii=False))
        output.write('\n')

    output.close()


if __name__ == "__main__":
    main(sys.argv[1:])
