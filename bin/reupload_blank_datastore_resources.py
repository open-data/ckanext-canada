#!/usr/bin/env python
"""
Gets Resources that are active in the DataStore
but do not have any data in the DataStore, and
resubmits them to be Xloadered.
"""

import click
import subprocess
from six import PY2
import configparser
from ckanapi import RemoteCKAN

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


def error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


def _get_datastore_tables(lc, offset, limit):
    click.echo("running with offset=%s limit=%s" % (offset, limit))
    result = lc.action.datastore_search(resource_id='_table_metadata', limit=limit, offset=offset)
    click.echo(result)
    return result.get('records', []), result.get('total', 0)


@click.command(short_help="Re-submits empty DataStore Resources to Xloader.")
@click.option('-c', '--config', required=True, envvar='REGISTRY_INI', type=click.File('r'),
              help='CKAN config INI file. Defaults to the $REGISTRY_INI environment variable.')
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to re-submit to Xloader. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
def reupload(config, resource_id, verbose):
    """
    Re-submits empty DataStore Resources to Xloader.
    """
    config_file = configparser.ConfigParser()
    config_file.read(config.name)
    try:
        site_url = config_file.get('app:main', 'ckan.site_url')
    except configparser.NoOptionError as e:
        error_message('Could not find ckan.site_url in config file.')
        return
    if not site_url:
        error_message('Could not find ckan.site_url in config file.')
        return

    errors = StringIO()
    num_packages = 0
    site_url = "http://ckan:5001"

    lc = RemoteCKAN(site_url)
    records, total = _get_datastore_tables(lc, 0, 10000)

    if not records:
        errors.write('No DataStore tables found.\n\n')

    for record in records:
        if verbose:
            click.echo("Checking DataStore count for Resource: %s" % record.get('name'))
        #TODO: get table info for resource id and check the meta.count == 0

    package_id = None
    # xloader submit argument is package_id or name
    xloader_submit_command = ['ckan', '--config=%s' % config.name, 'xloader', 'submit', '-y', package_id]
    if PY2:
        xloader_submit_command = ['ckan', 'ckan', '--config=%s' % config.name, 'xloader', 'submit', '-y', package_id]

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        error_message(errors.read())
    else:
        success_message('Re-submitted %s Packages to Xloader.' % num_packages)


reupload()
