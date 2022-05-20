#!/usr/bin/env python
# coding=utf-8

import codecs
from decimal import Decimal
from re import sub
import sys
import unicodecsv
from unicodedata import normalize
import yaml


FIELDNAMES = [
    u'reporting_period',
    u'line_number',
    u'member_name',
    u'province',
    u'role',
    u'meeting_hours',
    u'other_hours',
    u'remuneration',
    u'travel_expenses',
    u'notes_en',
    u'notes_fr',
    u'record_created',
    u'record_modified',
    u'user_modified',
    u'owner_org',
    u'owner_org_title',
]

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

error_csv = None
if sys.argv[1:]:
    error_csv = unicodecsv.DictWriter(open(sys.argv[1], 'wb'),
                                      fieldnames=FIELDNAMES,
                                      encoding='utf-8')
    error_csv.writeheader()

# get DAC member names
dac_member_yaml = open("../../ckanext/canada/tables/choices/dac_members.yaml", "r")
members = yaml.safe_load(dac_member_yaml)

try:
    for line in in_csv:
        # change money values such as $7,300.99 to 7300.99
        line['remuneration'] = Decimal(sub(r'[^\d.]', '', line['remuneration']))
        line['travel_expenses'] = Decimal(sub(r'[^\d.]', '', line['travel_expenses']))

        # change free text member names to a controlled list
        line[u'member_name'] = line[u'member_name'].strip()

        # map member names with typos where obvious
        if line[u'member_name'] == u'Adrian deSaldanha':
            best_match = u'de Saldanha, Adrian'
        elif line[u'member_name'] == u'Angie Gillis':
            best_match = u'Gillis, Angeline'
        elif line[u'member_name'] == u'Carola Swan':
            best_match = u'Swan, Carole'
        elif line[u'member_name'] == u'Cassandra':
            best_match = u'Dorrington, Cassandra'
        elif line[u'member_name'] == u'Fredrick Gorbet':
            best_match = u'Gorbet, Frederick'
        elif line[u'member_name'] == u'Inga Shaene':
            best_match = u'Sheane, Inga'
        elif line[u'member_name'] == u'Almeida Iris-Côté':
            best_match = u'Almeida-Côté, Iris'
        elif line[u'member_name'] in [u'M. Sheikh', u'M. Shiekh', u'Munir Shiekh']:
            best_match = u'Sheikh, Munir'
        elif line[u'member_name'] == u'M. Roberts':
            best_match = u'Roberts, Meena'
        elif line[u'member_name'] == u'N. Whipp':
            best_match = u'Whipp, Nancy'
        elif line[u'member_name'] == u'Norman Turbull':
            best_match = u'Turnbull, Norman'
        elif line[u'member_name'] == u'Raymond Crabbe':
            best_match = u'Crabbe, Ray'
        elif line[u'member_name'] == u'Ruby Philip-Kaytal':
            best_match = u'Philip-Katyal, Ruby'
        elif line[u'member_name'] == u'Wendy Key':
            best_match = u'Kei, Wendy'

        else:
            name_parts = line[u'member_name'].split(' ')
            matches = []
            for part in name_parts:
                part = part.strip()
                part = part.strip(',')
                part = part.lower()
                part = unicode(normalize('NFKD', part)
                               .encode('ASCII', 'ignore'),
                               'utf-8')

                for member in map(unicode, members.keys()):
                    if part in unicode(
                            normalize('NFKD', member.lower()).encode('ASCII', 'ignore'),
                            'utf-8'):
                        matches.append(member)
            if len(matches):
                best_match = max(set(matches), key=matches.count)
            else:
                best_match = 'NIL'
            if matches.count(best_match) > 1:
                line[u'member_name'] = best_match
            else:
                if error_csv:
                    error_csv.writerow(line)

        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
