#!/usr/bin/env python3

import sys
import os
import csv
import yaml

assert sys.argv[1], "Usage: service_program_ids_csv_to_choices.py csv-file"

OUTPUT_FILE = os.path.join(
    os.path.split(__file__)[0],
    '../ckanext/canada/tables/choices/service_program_ids.yaml')


prog_ids = {}

with open(sys.argv[1], 'r', encoding='utf-8-sig') as infile:
    c = csv.DictReader(infile)
    assert 'Program ID' in c.fieldnames, c.fieldnames
    assert 'Program Name (EN)' in c.fieldnames, c.fieldnames
    assert 'Program Name (FR)' in c.fieldnames, c.fieldnames
    assert 'Org ID on Open Gov recombinant datasets (where available)' in c.fieldnames, c.fieldnames
    assert 'Valid until fiscal year ending in' in c.fieldnames, c.fieldnames

    for rec in c:
        p = prog_ids.setdefault(rec['Program ID'], {'valid_orgs': []})

        if rec['Org ID on Open Gov recombinant datasets (where available)'] in p['valid_orgs']:
            sys.stderr.write(f'SKIPPING duplicate: {rec}\n')
            continue
        p['valid_orgs'].append(rec['Org ID on Open Gov recombinant datasets (where available)'])

        rec['Program Name (EN)'] = rec['Program Name (EN)'].replace('\N{NO-BREAK SPACE}', ' ').strip()
        if p.get('en') not in (None, rec['Program Name (EN)']):
            sys.stderr.write(f'unmatched EN name: {rec["Program Name (EN)"]!r} / {p["en"]!r}\n')
        if 'en' not in p or len(rec['Program Name (EN)']) < len(p['en']):
            # assume shorter is more generic
            p['en'] = rec['Program Name (EN)']

        rec['Program Name (FR)'] = rec['Program Name (FR)'].replace('\N{NO-BREAK SPACE}', ' ').strip()
        if p.get('fr') not in (None, rec['Program Name (FR)']):
            sys.stderr.write(f'unmatched FR name: {rec["Program Name (FR)"]!r} / {p["fr"]!r}\n')
        if 'fr' not in p or len(rec['Program Name (FR)']) < len(p['fr']):
            # assume shorter is more generic
            p['fr'] = rec['Program Name (FR)']

        rec['Valid until fiscal year ending in'] = int(rec['Valid until fiscal year ending in'])
        if p.get('valid_until_fiscal_end') not in (None, rec['Valid until fiscal year ending in']):
            sys.stderr.write(f'unmatched valid until {rec} / {p["valid_until_fiscal_end"]}\n')
        if rec['Valid until fiscal year ending in'] > p.get('valid_until_fiscal_end', 0):
            # assume later year is better
            p['valid_until_fiscal_end'] = rec['Valid until fiscal year ending in']

with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
    yaml.dump({k: v for (k, v) in sorted(prog_ids.items())}, outfile, allow_unicode=True)
