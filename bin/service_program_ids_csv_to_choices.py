#!/usr/bin/env python3

import sys
import os
import csv
import yaml

assert sys.argv[1], "Usage: service_program_ids_csv_to_choices.py csv-file"

OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/choices/service_program_ids.yaml')

CSV_ID = 'Program ID'
CSV_EN = 'Program Name (EN)'
CSV_FR = 'Program Name (FR)'
CSV_ORGS = 'Org ID on Open Gov recombinant datasets (where available)'
CSV_UNTIL = 'Valid until fiscal year ending in'


prog_ids = {}

with open(sys.argv[1], 'r', encoding='utf-8-sig') as infile:
    c = csv.DictReader(infile)
    assert CSV_ID in c.fieldnames, c.fieldnames
    assert CSV_EN in c.fieldnames, c.fieldnames
    assert CSV_FR in c.fieldnames, c.fieldnames
    assert CSV_ORGS in c.fieldnames, c.fieldnames
    assert CSV_UNTIL in c.fieldnames, c.fieldnames

    for rec in c:
        p = prog_ids.setdefault(rec['Program ID'], {'valid_orgs': []})

        if rec[CSV_ORGS] in p['valid_orgs']:
            sys.stderr.write(f'SKIPPING duplicate: {rec}\n')
            continue
        p['valid_orgs'].append(rec[CSV_ORGS])

        rec[CSV_EN] = rec[CSV_EN].replace('\N{NO-BREAK SPACE}', ' ').strip()
        if p.get('en') not in (None, rec[CSV_EN]):
            sys.stderr.write(f'unmatched EN name: {rec[CSV_EN]!r} / {p["en"]!r}\n')
        if 'en' not in p or len(rec[CSV_EN]) < len(p['en']):
            # assume shorter is more generic
            p['en'] = rec[CSV_EN]

        rec[CSV_FR] = rec[CSV_FR].replace('\N{NO-BREAK SPACE}', ' ').strip()
        if p.get('fr') not in (None, rec[CSV_FR]):
            sys.stderr.write(f'unmatched FR name: {rec[CSV_FR]!r} / {p["fr"]!r}\n')
        if 'fr' not in p or len(rec[CSV_FR]) < len(p['fr']):
            # assume shorter is more generic
            p['fr'] = rec[CSV_FR]

        rec[CSV_UNTIL] = int(rec[CSV_UNTIL])
        if p.get('valid_until_fiscal_end') not in (None, rec[CSV_UNTIL]):
            sys.stderr.write(
                f'unmatched valid until {rec} / {p["valid_until_fiscal_end"]}\n'
            )
        if rec[CSV_UNTIL] > p.get('valid_until_fiscal_end', 0):
            # assume later year is better
            p['valid_until_fiscal_end'] = rec[CSV_UNTIL]

with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
    yaml.dump(
        {k: v for (k, v) in sorted(prog_ids.items())},
        outfile,
        allow_unicode=True
    )
