#!/usr/bin/env python3
"""
Gets the ati-informal-requests-analytics.csv from the SMB
and filters out the current month's rows and then patches the
Resource on the Registry.
"""

import os
import click
import csv
import traceback
import tempfile
from datetime import datetime
import subprocess
from codecs import BOM_UTF8
from io import StringIO

BOM = "\N{bom}"


def error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


def get_smb_file():
    """
    Get the file path generated from Drupal
    The SMB directories are different on some servers
    hence the checks for the different file paths
    """
    check_paths = [
        '/opt/tbs/ckan/smb_portal/portal/public/ati-informal-requests-analytics.csv',
        '/opt/tbs/ckan/smb/portal/public/ati-informal-requests-analytics.csv',
        '/opt/tbs/ckan/smb_portal/portal/public/static/'
        'ati-informal-requests-analytics.csv',
        '/opt/tbs/ckan/smb/portal/public/static/'
        'ati-informal-requests-analytics.csv',]
    for file in check_paths:
        if os.path.isfile(file):
            return file
    error_message(
        '/opt/tbs/ckan/[smb_portal|smb]/portal/public/[static/]'
        'ati-informal-requests-analytics.csv does not exist.')


@click.command(
        short_help="Filters ATI Informal Analytics CSV "
                   "and uploads to Registry Resource.")
@click.option('-c', '--config', required=True,
              envvar='REGISTRY_INI', type=click.File('r'),
              help='CKAN config INI file. Defaults to the '
                   '$REGISTRY_INI environment variable.')
@click.option('-r', '--resource-id', required=False,
              type=click.STRING, default='e664cf3d-6cb7-4aaa-adfa-e459c2552e3e',
              help='Resource ID to patch the file to. '
                   'Defaults to e664cf3d-6cb7-4aaa-adfa-e459c2552e3e.')
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
def update(config, resource_id, verbose):
    """
    Filters ATI Informal Analytics CSV and uploads to Registry Resource.
    """
    generated_file = get_smb_file()
    if not generated_file:
        return
    temp_dir = tempfile.TemporaryDirectory()
    temp_file = os.path.join(temp_dir.name, 'ati-informal-requests-analytics.csv')

    today = datetime.today()

    errors = StringIO()
    skipped_rows = 0
    command = ['ckanapi', 'action', 'resource_patch', '--config=%s' % config.name,
               'id=%s' % resource_id, 'upload@%s' % temp_file]

    try:
        with open(generated_file, 'r') as df:
            reader = csv.DictReader(df)
            with open(temp_file, 'w') as cf:
                writer = csv.DictWriter(cf, reader.fieldnames)
                writer.writeheader()
                row_index = 0
                for row in reader:
                    try:
                        if 'Year' in row:
                            year_key = 'Year'
                        elif '%sYear' % BOM_UTF8 in row:
                            year_key = '%sYear' % BOM_UTF8
                        elif '%sYear' % BOM in row:
                            year_key = '%sYear' % BOM
                        else:
                            errors.write('Failed to patch resource %s '
                                         'with errors:\n\nCannot find Year header.'
                                         % resource_id)
                            raise LookupError
                        if (
                          int(row[year_key]) == int(today.year) and
                          int(row['Month']) == int(today.month)):
                            skipped_rows += 1
                            if verbose:
                                click.echo('Skipping row %s, excluding Y,M: %s,%s' %
                                           (row_index, int(row[year_key]),
                                            int(row['Month'])))
                            continue
                        writer.writerow(row)
                    except ValueError:
                        pass
                    row_index += 1
        if skipped_rows:
            success_message('Filtered %s rows, excluded Y,M: %s,%s' %
                            (skipped_rows, today.year, today.month))
        if verbose:
            success_message('Executing command:\n\n%s\n' %
                            subprocess.list2cmdline(command))
        p = subprocess.run(command)
        p.check_returncode()
    except LookupError:
        pass
    except Exception as e:
        errors.write('Failed to patch resource %s with errors:\n\n%s' %
                     (resource_id, e))
        if verbose:
            errors.write('\n')
            traceback.print_exc(file=errors)
        pass
    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        error_message(errors.read())
    else:
        success_message('Patched resource %s with new CSV file' % resource_id)
    temp_dir.cleanup()


update()
