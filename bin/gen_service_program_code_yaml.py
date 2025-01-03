#!/usr/bin/env python3
"""
Converts supplied EN/FR CSV files into a Recombinant YAML choice file.

See resources:
https://open.canada.ca/data/en/dataset/3c371e57-d487-49fa-bb0d-352ae8dd6e4e

CSV inputs should contain 2 columns:
Program ID, Program Name
"""

import click
import csv
import yaml

BOM = "\N{bom}"


def error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


@click.command(short_help="Generates a YAML choices file from a CSV "
                          "file of Service Inventory Program Codes and Names.")
@click.option('-e', '--input-english', required=True, type=click.File('r'),
              help='The English input CSV file.')
@click.option('-f', '--input-french', required=True, type=click.File('r'),
              help='The French input CSV file.')
@click.option('-o', '--output', required=True, type=click.File('w'),
              help='The output YAML file.')
@click.option('-c', '--codes-only', is_flag=True, type=click.BOOL,
              help='Only generate a choice file of the '
                   'codes, excluding the Program Names.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL,
              help='Increase verbosity.')
def generate_program_code_yaml(input_english, input_french,
                               output, codes_only=False, verbose=False):

    choices = {}

    with open(input_english.name, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row[0] or row[0] in choices:
                continue
            if codes_only:
                choices[row[0]] = row[0]
                continue
            choices[row[0]] = {'en': row[1]}

    with open(input_french.name, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row[0]:
                continue
            if codes_only and row[0] in choices:
                continue
            if not codes_only and 'fr' in choices[row[0]]:
                continue
            if codes_only:
                choices[row[0]] = row[0]
                continue
            choices[row[0]]['fr'] = row[1]

    choices = dict(sorted(choices.items(), key=lambda x: x[0].lower()))

    with open(output.name, 'w') as f:
        output.write(yaml.safe_dump(choices, encoding='utf-8',
                                    allow_unicode=True).decode('utf-8'))

    success_message('DONE!')


generate_program_code_yaml()
