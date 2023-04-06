#!/usr/bin/env python

import sys
import unicodecsv
import codecs

merge_orgs = [
    'ghl-lgc',
    'iga-aig',
    'mdi-mid',
    'miga-maig',
    'dpm-vpm',
    'pkcc-pcprc',
    'ql-lq',
    'srp-rsp',
    'nsira-ossnr',
    'ocsec-bccst',
    'snsicp-scpssnr',
    'sirc-csars',
    'jfpc-cfp',
    'pco-bcp',
]

seen_refs = set()
dup_refs = set()

with open(sys.argv[1], 'rb') as f:
    assert f.read(3) == codecs.BOM_UTF8

    in_csv = unicodecsv.DictReader(f, encoding='utf-8')
    for pk in ('tracking_number', 'reference_number', 'ref_number', 'year'):
        if pk in in_csv.fieldnames:
            break
    else:
        assert 0, 'no pk field?'

    for line in in_csv:
        if line['owner_org'] in merge_orgs:
            if line[pk] in seen_refs:
                dup_refs.add(line[pk])
            seen_refs.add(line[pk])

with open(sys.argv[1], 'rb') as f:
    assert f.read(3) == codecs.BOM_UTF8

    out_csv = unicodecsv.DictWriter(sys.stdout, fieldnames=in_csv.fieldnames, encoding='utf-8')
    out_csv.writeheader()

    in_csv = unicodecsv.DictReader(f, encoding='utf-8')
    for line in in_csv:
        if line['owner_org'] in merge_orgs:
            if line[pk] in dup_refs:
                out_csv.writerow(line)
