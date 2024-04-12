#!/usr/bin/env python3

import unicodecsv
import sys
import codecs
import json
from decimal import Decimal, InvalidOperation

FIELDNAMES = ['year', 'mandate_description_en', 'mandate_description_fr', 'operational_activities_kdollars', 'key_stakeholders_kdollars', 'training_kdollars', 'other_kdollars', 'internal_governance_kdollars', 'non_public_servants_kdollars', 'public_servants_kdollars', 'hospitality_kdollars', 'conference_fees_kdollars', 'minister_kdollars', 'travel_compared_fiscal_year_en', 'travel_compared_fiscal_year_fr', 'hospitality_compared_fiscal_year_en', 'hospitality_compared_fiscal_year_fr', 'conference_fees_compared_fiscal_year_en', 'conference_fees_compared_fiscal_year_fr', 'minister_compared_fiscal_year_en', 'minister_compared_fiscal_year_fr', 'record_created', 'record_modified', 'user_modified', 'owner_org', 'owner_org_title']

assert sys.stdin.read(3) == codecs.BOM_UTF8

in_csv = unicodecsv.DictReader(sys.stdin, encoding='utf-8')
out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=FIELDNAMES, encoding='utf-8')
out_csv.writeheader()

# collect all records so we can fill in missing mandate_description_en/fr on first years
org_year = {}

try:
    for line in in_csv:
        org_year[line['owner_org'], line['year']] = line

    def next_line(line):
        "return line from same org following year"
        return org_year[line['owner_org'], str(int(line['year'])+1)]

    for oy in sorted(org_year):
        line = org_year[oy]

        if int(line['year']) >= 2018:
            sys.stderr.write('discarding {0}\n'.format(repr(oy)))
            continue
        try:
            if not line['mandate_description_en']:
                line['mandate_description_en'] = next_line(line)['mandate_description_en']
        except KeyError:
            line['mandate_description_en'] = ''
        try:
            if not line['mandate_description_fr']:
                line['mandate_description_fr'] = next_line(line)['mandate_description_fr']
        except KeyError:
            line['mandate_description_fr'] = ''
        line['operational_activities_kdollars'] = ''
        line['key_stakeholders_kdollars'] = ''
        line['training_kdollars'] = ''
        line['internal_governance_kdollars'] = ''
        ps = line.pop('public_servants')
        try:
            ps = Decimal(ps.replace(',', ''))
        except InvalidOperation:
            sys.stderr.write('discarding {0} {1}\n'.format(repr(oy), repr(ps)))
            continue
        nps = Decimal(line.pop('non_public_servants').replace(',', ''))
        line['public_servants_kdollars'] = str(ps)
        line['non_public_servants_kdollars'] = str(nps)
        line['travel_compared_fiscal_year_en'] = \
            u'Public Servants: {0} {1};\nNon-Public Servants: {2} {3}'.format(
                str(ps),
                line.pop('public_servant_compared_fiscal_year_en'),
                str(nps),
                line.pop('non_public_servant_compared_fiscal_year_en'))
        line['travel_compared_fiscal_year_fr'] = \
            u'Voyages des fonctionnaires: {0} {1};\nVoyages des non-fonctionnaires: {2} {3}'.format(
                str(ps),
                line.pop('public_servant_compared_fiscal_year_fr'),
                str(nps),
                line.pop('non_public_servant_compared_fiscal_year_fr'))
        line['hospitality_kdollars'] = line.pop('hospitality').replace(',', '')
        line['conference_fees_kdollars'] = line.pop('conference_fees').replace(',', '')
        try:
            m = Decimal(line.pop('minister').replace(',', ''))
        except InvalidOperation:
            m = 0
        line['minister_kdollars'] = str(m)
        if 'warehouse' not in sys.argv[1:]:
            line['user_modified'] = '*'  # special "we don't know" value
        out_csv.writerow(line)

except KeyError:
    if 'warehouse' in sys.argv:
        sys.exit(85)
    else:
        raise
