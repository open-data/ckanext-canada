#!/usr/bin/env python3

import gzip
import json
import hashlib
from pathlib import Path
from sys import stderr, stdout, argv
from csv import DictReader
from collections import Counter

import click

METADATA_COLLECTION_COLUMNS = {
    'primary': 'meta:primary',
    'code': 'meta:code',
    'api': 'meta:api',
    'app': 'meta:app',
    'fgp': 'meta:fgp',
    'federated': 'meta:federated',
    'publication': 'meta:publication',
    'transition': 'meta:briefing_pkg',
    'transition_deputy': 'meta:briefing_pkg',
    'parliament_committee': 'meta:parliament_pkg',
    'parliament_committee_deputy': 'meta:parliament_pkg',
    'parliament_report': 'meta:parliament_report',
    'question_period': 'meta:question_period',
}

ROWS_PD_TYPE_COLUMNS = {
    'ati.csv': 'rows:ati',
    'ati-nil.csv': 'rows:ati',
    'contractsa.csv': 'rows:contracts',
    'contracts.csv': 'rows:contracts',
    'contracts-nil.csv': 'rows:contracts',
    'consultations.csv': 'rows:consultations',
    'grants.csv': 'rows:grants',
    'grants-nil.csv': 'rows:grants',
    'hospitalityq.csv': 'rows:travel_hospitality',
    'hospitalityq-nil.csv': 'rows:travel_hospitality',
    'travela.csv': 'rows:travel_hospitality',
    'travelq.csv': 'rows:travel_hospitality',
    'travelq-nil.csv': 'rows:travel_hospitality',
    'reclassification.csv': 'rows:reclassification',
    'reclassification-nil.csv': 'rows:reclassification',
    'wrongdoing.csv': 'rows:wrongdoing',
    'dac.csv': 'rows:dac',
    'briefingt.csv': 'rows:briefingt',
    'qpnotes.csv': 'rows:qpnotes',
}

COLUMNS = sorted(
    set(METADATA_COLLECTION_COLUMNS.values()) |
    set(ROWS_PD_TYPE_COLUMNS.values())
)

@click.command(help='''
Generate report to stdout by comparing PREVIOUS_DIR and CURRENT_DIR data
Each directory is expected to have filtered/*.csv data files and a single
metadata.jsonl.gz file at the base level
''')
@click.option('--header/--no-header', default=False, help='output header row')
@click.argument('period_label')
@click.argument('previous_dir')
@click.argument('current_dir')
def cli(header, period_label, previous_dir, current_dir):
    if header:
        stdout.write(
            '\N{BOM}period,org,t/a,∑meta,∑rows,' +
            ','.join(col for col in COLUMNS)
        )

    # active_count, total_count = counts[col]
    counts = {col:(Counter(), Counter()) for col in COLUMNS}

    stderr.write('[» ] metadata…\r')
    existing_metadata = collect_existing_metadata(previous_dir)
    stderr.write(f'[»»\r\n')
    count_metadata(current_dir, existing_metadata, counts)
    del existing_metadata

    for csv_name, col in sorted(ROWS_PD_TYPE_COLUMNS.items()):
        stderr.write(f'[» ] {csv_name} rows…\r')
        existing_rows = collect_existing_rows(previous_dir, csv_name)
        stderr.write(f'[»»\r\n')
        count_rows(current_dir, csv_name, existing_rows, counts[col])

    sum_active = Counter()
    sum_total = Counter()
    orgs = set()
    for col, (active_count, total_count) in counts.items():
        orgs |= active_count.keys()
        orgs |= total_count.keys()
        sum_active[col] += sum(active_count.values())
        sum_total[col] += sum(total_count.values())

    sum_active_meta = sum(
        sum_active[col] for col in COLUMNS if col.startswith('meta:'))
    sum_active_rows = sum(
        sum_active[col] for col in COLUMNS if col.startswith('rows:'))
    stdout.write(
        f'\n{period_label},∑orgs,active,{sum_active_meta},{sum_active_rows},' +
        ','.join(str(sum_active[col]) for col in COLUMNS)
    )
    sum_total_meta = sum(
        sum_total[col] for col in COLUMNS if col.startswith('meta:'))
    sum_total_rows = sum(
        sum_total[col] for col in COLUMNS if col.startswith('rows:'))
    stdout.write(
        f'\n{period_label},∑orgs,total,{sum_total_meta},{sum_total_rows},' +
        ','.join(str(sum_total[col]) for col in COLUMNS)
    )

    for org in sorted(orgs):
        sum_active_meta = sum(
            counts[col][0][org] for col in COLUMNS if col.startswith('meta:')
        )
        sum_active_rows = sum(
            counts[col][0][org] for col in COLUMNS if col.startswith('rows:')
        )
        stdout.write(
            f'\n{period_label},{org},active,{sum_active_meta},{sum_active_rows},' +
            ','.join(str(counts[col][0][org]) for col in COLUMNS)
        )
        sum_total_meta = sum(
            counts[col][1][org] for col in COLUMNS if col.startswith('meta:'))
        sum_total_rows = sum(
            counts[col][1][org] for col in COLUMNS if col.startswith('rows:'))
        stdout.write(
            f'\n{period_label},{org},total,{sum_total_meta},{sum_total_rows},' +
            ','.join(str(counts[col][1][org]) for col in COLUMNS)
        )


def collect_existing_metadata(previous_dir):
    '''
    return a set of hashes for metadata in previous_dir/metadata.jsonl.gz,
    excluding the organization fields to avoid counting org changes
    as metadata changes
    '''
    existing = set()
    with gzip.open(Path(previous_dir, 'metadata.jsonl.gz')) as f:
        for line in f:
            m = json.loads(line)
            del m['owner_org']
            del m['organization']
            if m['collection'] not in METADATA_COLLECTION_COLUMNS:
                continue
            existing.add(
                hashlib.md5(
                    json.dumps(m, sort_keys=True).encode('utf8')
                ).digest()
            )
    return existing


def count_metadata(current_dir, existing_metadata, counts):
    '''
    update counts with records found in current_dir/metadata.jsonl.gz,
    compating against existing_metadata
    '''
    with gzip.open(Path(current_dir, 'metadata.jsonl.gz')) as f:
        for line in f:
            m = json.loads(line)
            org = m['organization']['name']
            del m['owner_org']
            del m['organization']
            try:
                col = METADATA_COLLECTION_COLUMNS[m['collection']]
            except KeyError:
                assert m['collection'] in ('geogratis',)
                continue
            active_count, total_count = counts[col]
            total_count[org] += 1
            h = hashlib.md5(
                json.dumps(m, sort_keys=True).encode('utf8')
            ).digest()
            if h not in existing_metadata:
                active_count[org] += 1


def collect_existing_rows(previous_dir, csv_name):
    '''
    return a set of hashes for rows in previous_dir/filtered/csv_name,
    excluding the organization fields to avoid counting org changes
    as row changes
    '''
    existing = set()
    with open(Path(previous_dir, 'filtered', csv_name)) as f:
        csv = DictReader(f)
        for row in csv:
            del row['owner_org']
            del row['owner_org_title']
            existing.add(
                hashlib.md5(repr(list(row.values())).encode('utf8')).digest()
            )

    return existing


def count_rows(current_dir, csv_name, existing_rows, col_counts):
    '''
    update counts with rows found in current_dir/filtered/csv_name,
    comparing against existing_rows
    '''
    with open(Path(current_dir, 'filtered', csv_name)) as f:
        csv = DictReader(f)
        for row in csv:
            org = row['owner_org']
            del row['owner_org']
            del row['owner_org_title']
            active_count, total_count = col_counts
            total_count[org] += 1
            h = hashlib.md5(repr(list(row.values())).encode('utf8')).digest()
            if h not in existing_rows:
                active_count[org] += 1

cli()
