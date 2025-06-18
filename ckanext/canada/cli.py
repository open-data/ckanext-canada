import csv
import json
import sys
import click
import traceback
from io import StringIO, BytesIO
import gzip
import requests
from collections import defaultdict

from typing import Optional, Union, cast, Generator, Dict, Any, List
from ckan.types import Context

from urllib.parse import urlparse

from ckan.logic import get_action
from ckan import model
from ckan.cli.db import db
from itertools import groupby

from ckanapi import (
    LocalCKAN,
    NotFound,
    ValidationError
)

import ckan.plugins.toolkit as toolkit

import ckanext.datastore.backend.postgres as datastore

from ckanext.canada import triggers

BOM = "\N{bom}"


def _resource_size_update(size_report: str):
    registry = LocalCKAN()
    size_report_file = open(size_report, "r")
    reader = csv.DictReader(size_report_file)
    for row in reader:
        uuid = row["uuid"]
        resource_id = row["resource_id"]
        new_size = str(row["found_file_size"])

        try:
            if new_size == 'N/A':
                continue
            resource = registry.call_action('resource_patch',
                                            {'id': resource_id, 'size': new_size}
                                            )
            print("Updated: ", [uuid, resource_id, resource.get("size")])
        except NotFound:
            print("{0} dataset not found".format(uuid))
    size_report_file.close()


def _resource_https_update(https_report: str, https_alt_report: str):
    """
    This function updates all broken http links into https links.
    https_report: the report with all of the links (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http
            /blob/main/orgs_http_data.json.
    https_alt_report: the report with links where alternates exist (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http
            /blob/main/https_alternative_count.json.
    For more specifications about the files in use please visit,
    https://github.com/open-data/opengov-orgs-http.
    """
    alt_file = open(https_alt_report, "r")
    alt_data = json.load(alt_file)

    https_file = open(https_report, "r")
    data = json.load(https_file)
    log = open("error.log", "w")

    def check_https(check_url: str,
                    check_org: str,
                    check_data: Any):
        for organization in check_data:
            if organization['org'] == check_org:
                for url in organization['urls']:
                    if check_url == url:
                        return True
        return False

    local_ckan = LocalCKAN()

    for org in data:
        for res in data[org]:
            if org == 'Statistics Canada | Statistique Canada':
                https_exist = True
            elif res['collection'] in ['fgp', 'federated']:
                https_exist = False
            else:
                https_exist = check_https(res['url'], org, alt_data)

            if https_exist and res['url_type'] == 'http':
                try:
                    https_url = res['url'].replace('http://', 'https://')
                    resource = local_ckan.call_action('resource_show',
                                                      {'id': res['id']})
                    if urlparse(resource['url']).scheme == 'http':
                        local_ckan.call_action('resource_patch',
                                               {'id': res['id'],
                                                'url': https_url})
                        log.write('Url for resource %s updated %s\n' %
                                  (res['id'], https_url))
                except NotFound:
                    log.write('Resource %s not found\n' % res['id'])
                except ValidationError as e:
                    log.write('Resource %s failed validation %s\n' %
                              (res['id'], str(e.error_dict)))
    log.close()

def _bulk_validate():
    """
    Usage: ckanapi search datasets include_private=true -c $CONFIG_INI |
    ckan -c $CONFIG_INI canada bulk-validate

    Use this command to bulk validate the resources. Any resources which
    are already in datastore but not validated will be removed.
    """
    log = open("bulk_validate.log", "w")
    datastore_removed = 0
    validation_queue = 0

    for line in sys.stdin.readlines():
        package = json.loads(line)
        for resource in package['resources']:
            if resource.get('url_type') == 'upload':
                # remove any non-validated resources from datastore
                if resource['datastore_active'] and \
                        resource.get('validation_status', '') != 'success':
                    try:
                        toolkit.get_action('datastore_search')(
                            {}, {'resource_id': resource['id']})
                        toolkit.get_action('datastore_delete')(
                            {},
                            {'resource_id': resource['id'],
                                'ignore_auth': True,
                                'force': True})
                        datastore_removed += 1
                        log.write("\nRemoving resource %s from datastore" %
                                  resource['id'])
                    except NotFound:
                        log.write("\n[ERROR]: Unable to remove resource "
                                  "%s from datastore - Resource not found"
                                  % resource['id'])

                # validate CSV resources which are uploaded to cloudstorage
                if resource.get('format', '').upper() == 'CSV':
                    try:
                        toolkit.get_action('resource_validation_run')(
                            {}, {'resource_id': resource['id'],
                                 'async': True,
                                 'ignore_auth': True})
                        validation_queue += 1
                        log.write("\nResource %s sent to the validation "
                                  "queue" % resource['id'])
                    except NotFound:
                        log.write("\n[ERROR]: Unable to send resource %s "
                                  "to validation queue - Resource not "
                                  "found" % resource['id'])

    log.write("\n\nTotal resources removed from datastore: " +
              str(datastore_removed))
    log.write("\nTotal resources sent to validation queue: " +
              str(validation_queue))

    log.close()


def _update_inventory_votes(json_name: str):
    with open(json_name) as j:
        votes = json.load(j)

    registry = LocalCKAN()
    for org in votes:
        print(org, len(votes[org]),)
        rs = registry.action.recombinant_show(
            dataset_type='inventory',
            owner_org=org)
        resource_id = rs['resources'][0]['id']
        result = registry.action.datastore_search(
            resource_id=resource_id,
            limit=len(votes[org]),
            filters={'ref_number': list(votes[org])})

        update = []
        for r in result['records']:
            expected = votes[org][r['ref_number']]
            if r['user_votes'] != expected:
                r['user_votes'] = expected
                del r['_id']
                update.append(r)

        print(len(update))

        if update:
            registry.action.datastore_upsert(
                resource_id=resource_id,
                records=update)


def get_commands():
    return canada


@click.group(short_help="Canada management commands")
def canada():
    """Canada management commands.
    """
    pass


@canada.command(short_help="Updates/creates database triggers.")
def update_triggers():
    """
    Create/update triggers used by PD tables
    """
    triggers.update_triggers()


@canada.command(short_help="Load Inventory Votes from a CSV file.")
@click.argument("votes_json")
def update_inventory_votes(votes_json: str):
    """

    Full Usage:\n
        canada update-inventory-votes <votes.json>
    """
    _update_inventory_votes(votes_json)


@canada.command(short_help="Tries to update resource sizes from a CSV file.")
@click.argument("resource_sizes_csv")
def resource_size_update(resource_sizes_csv: str):
    """
    Tries to update resource sizes from a CSV file.

    Full Usage:\n
        canada resource-size-update <resource_sizes.csv>
    """
    _resource_size_update(resource_sizes_csv)


@canada.command(short_help="Tries to replace resource URLs from http to https.")
@click.argument("https_report")
@click.argument("https_alt_report")
def update_resource_url_https(https_report: str, https_alt_report: str):
    """
    This function updates all broken http links into https links.
    https_report: the report with all of the links (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http
            /blob/main/orgs_http_data.json.
    https_alt_report: the report with links where alternates exist (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http
            /blob/main/https_alternative_count.json.
    For more specifications about the files in use please visit,
    https://github.com/open-data/opengov-orgs-http.

    Full Usage:\n
        canada update-resource-url-https <https_report> <https_alt_report>
    """
    _resource_https_update(https_report,
                           https_alt_report)


@canada.command(short_help="Runs ckanext-validation for all supported resources.")
def bulk_validate():
    """
    Use this command to bulk validate the resources. Any resources which
    are already in datastore but not validated will be removed.

    Requires stdin

    Full Usage:\n
         ckanapi search datasets include_private=true -c $CONFIG_INI |\n
         ckan -c $CONFIG_INI canada bulk-validate
    """
    _bulk_validate()


@canada.command(short_help="Deletes rows from the activity table.")
@click.option(
    "-d",
    "--days",
    help="Number of days to go back. E.g. 120 will "
         "keep 120 days of activities. Default: 90",
    default=90
)
@click.option(
    "-i",
    "--include-types",
    help="Activity types to include in the "
         "deletion. E.g. 'resource create' (MULTIPLE)",
    default=None,
    multiple=True
)
@click.option(
    "-e",
    "--exclude-types",
    help="Activity types to exclude in the "
         "deletion. E.g. 'datastore create' (MULTIPLE)",
    default=None,
    multiple=True
)
@click.option("-q", "--quiet", is_flag=True,
              help="Suppress human interaction.", default=False)
def delete_activities(days: Optional[int] = 90,
                      include_types: Optional[Union[str, List[str]]] = None,
                      exclude_types: Optional[Union[str, List[str]]] = None,
                      quiet: Optional[bool] = False):
    """
    Delete rows from the activity table past a certain number of days.
    """
    if include_types and len(include_types) == 1:
        include_types = f"('{include_types[0]}')"
    if exclude_types and len(exclude_types) == 1:
        exclude_types = f"('{exclude_types[0]}')"
    if include_types:
        click.echo(f'Including activity_type {include_types}')
    if exclude_types:
        click.echo(f'Excluding activity_type {exclude_types}')
    activity_count = model.Session.execute(
        "SELECT count(*) FROM activity "
        "WHERE timestamp < NOW() - INTERVAL '{d} days' {i} {e};"
        .format(
            d=days,
            i="AND activity_type IN {i}".format(i=include_types) if
            include_types else "",
            e="AND activity_type NOT IN {e}".format(e=exclude_types) if
            exclude_types else "")) \
        .fetchall()[0][0]

    if not bool(activity_count):
        click.echo("\nNo activities found past {d} days".format(d=days))
        return

    if not quiet:
        click.confirm("\nAre you sure you want to delete {num} activities?".format(
            num=activity_count), abort=True)

    model.Session.execute(
        "DELETE FROM activity "
        "WHERE timestamp < NOW() - INTERVAL '{d} days' {i} {e};"
        .format(
            d=days,
            i="AND activity_type IN {i}".format(i=include_types) if
            include_types else "",
            e="AND activity_type NOT IN {e}".format(e=exclude_types) if
            exclude_types else ""))
    model.Session.commit()

    click.echo("\nDeleted {num} rows from the activity table".format(
        num=activity_count))


def _get_site_user_context() -> Context:
    user = get_action('get_site_user')({'ignore_auth': True}, {})
    return cast(Context, {"user": user['name'], "ignore_auth": True})


def _get_datastore_tables(verbose: Optional[bool] = False) -> List[str]:
    """
    Returns a list of resource ids (table names) from
    the DataStore database.
    """
    tables = get_action('datastore_search')(_get_site_user_context(),
                                            {"resource_id": "_table_metadata",
                                             "offset": 0,
                                             "limit": 100000})
    if not tables:
        return []
    if verbose:
        click.echo("Gathered %s table names from the DataStore." % len(
            tables.get('records', [])))
    return [r.get('name') for r in tables.get('records', [])]


def _get_datastore_resources(valid: Optional[bool] = True,
                             is_datastore_active: Optional[bool] = True,
                             verbose: Optional[bool] = False) -> List[str]:
    """
    Returns a list of resource ids that are DataStore
    enabled and that are of upload url_type.

    Defaults to only return valid resources.
    """
    results = True
    counter = 0
    batch_size = 1000
    datastore_resources = []
    while results:
        _packages = get_action('package_search')(
            _get_site_user_context(),
            {"q": "*:*",
             "start": counter,
             "rows": batch_size,
             "include_private": True})['results']
        if _packages:
            if verbose:
                if is_datastore_active:
                    click.echo("Looking through %s packages "
                               "to find DataStore Resources." % len(_packages))
                else:
                    click.echo("Looking through %s packages "
                               "to find NON-DataStore Resources." % len(_packages))
                if valid is None:
                    click.echo("Gathering Invalid and Valid Resources...")
                elif valid is True:
                    click.echo("Gathering only Valid Resources...")
                elif valid is False:
                    click.echo("Gathering only Invalid Resources...")
            counter += len(_packages)
            for _package in _packages:
                for _resource in _package.get('resources', []):
                    # already in return list
                    if _resource.get('id') in datastore_resources:
                        continue
                    # we only want upload or link types
                    if (
                      _resource.get('url_type') != 'upload' and
                      _resource.get('url_type') != ''):
                        continue
                    if is_datastore_active and not _resource.get('datastore_active'):
                        continue
                    if not is_datastore_active and _resource.get('datastore_active'):
                        continue
                    if valid is None:
                        datastore_resources.append(_resource.get('id'))
                        continue
                    validation_status = _resource.get('validation_status')
                    if valid is True and validation_status == 'success':
                        datastore_resources.append(_resource.get('id'))
                        continue
                    if valid is False and validation_status == 'failure':
                        datastore_resources.append(_resource.get('id'))
                        continue
        else:
            results = False
    if verbose:
        if is_datastore_active:
            click.echo("Gathered %s DataStore Resources." %
                       len(datastore_resources))
        else:
            click.echo("Gathered %s NON-DataStore Resources." %
                       len(datastore_resources))
    return datastore_resources


def _get_datastore_count(context: Context,
                         resource_id: str,
                         verbose: Optional[bool] = False,
                         status: Optional[int] = 1,
                         max: Optional[int] = 1):
    """
    Returns the count of rows in the DataStore table for a given resource ID.
    """
    if verbose:
        click.echo("%s/%s -- Checking DataStore record "
                   "count for Resource %s" % (status, max, resource_id))
    info = get_action('datastore_search')(
        context, {"resource_id": resource_id, "limit": 0})
    return info.get('total')


def _error_message(message: Any):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def _success_message(message: Any):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


@canada.command(short_help="Sets datastore_active to False for Invalid Resources.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to set the datastore_active flag. Defaults to None.')
@click.option('-d', '--delete-table-views', is_flag=True,
              type=click.BOOL, help='Deletes any Datatable Views from the Resource.')
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True,
              type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True,
              type=click.BOOL,
              help='List the Resource IDs instead of setting the flags to false.')
def set_datastore_false_for_invalid_resources(
        resource_id: Optional[str] = None,
        delete_table_views: Optional[bool] = False,
        verbose: Optional[bool] = False,
        quiet: Optional[bool] = False,
        list: Optional[bool] = False):
    """
    Sets datastore_active to False for Resources that are
    not valid but are empty in the DataStore database.
    """

    try:
        from ckanext.datastore.logic.action import set_datastore_active_flag
    except ImportError:
        _error_message("DataStore extension is not active.")
        return

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_set = []
    status = 1
    if not resource_id:
        # gets invalid Resources, w/ datastore_active=1
        resource_ids = _get_datastore_resources(valid=False, verbose=verbose)
        max = len(resource_ids)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_set:
                continue
            if resource_id in datastore_tables:
                try:
                    count = _get_datastore_count(
                        context, resource_id,
                        verbose=verbose, status=status, max=max)
                    if int(count) == 0:
                        if verbose:
                            click.echo("%s/%s -- Resource %s has %s "
                                       "rows in DataStore. Let's fix this one..." % (
                                           status, max, resource_id, count))
                        resource_ids_to_set.append(resource_id)
                    elif verbose:
                        click.echo("%s/%s -- Resource %s has %s rows "
                                   "in DataStore. Skipping..." % (
                                       status, max, resource_id, count))
                except Exception as e:
                    if verbose:
                        errors.write('Failed to get DataStore info '
                                     'for Resource %s with errors:\n\n%s' % (
                                         resource_id, e))
                        errors.write('\n')
                        traceback.print_exc(file=errors)
                    pass
            status += 1
    else:
        try:
            count = _get_datastore_count(context, resource_id, verbose=verbose)
            if int(count) == 0:
                if verbose:
                    click.echo("1/1 -- Resource %s has %s rows "
                               "in DataStore. Let's fix this one..." % (
                                   resource_id, count))
                resource_ids_to_set = [resource_id]
            elif verbose:
                click.echo("1/1 -- Resource %s has %s rows "
                           "in DataStore. Skipping..." % (
                               resource_id, count))
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info '
                             'for Resource %s with errors:\n\n%s' % (
                                 resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_set and not quiet and not list:
        click.confirm("Do you want to set datastore_active flag "
                      "to False for %s Invalid Resources?" %
                      len(resource_ids_to_set), abort=True)

    status = 1
    max = len(resource_ids_to_set)
    for id in resource_ids_to_set:
        if list:
            click.echo(id)
        else:
            try:
                set_datastore_active_flag(cast(Context, {'model': model}),
                                          {"resource_id": id}, False)
                if verbose:
                    click.echo("%s/%s -- Set datastore_active "
                               "flag to False for Invalid Resource %s" % (
                                   status, max, id))
                if delete_table_views:
                    views = get_action('resource_view_list')(context, {"id": id})
                    if views:
                        for view in views:
                            if view.get('view_type') == 'datatables_view':
                                get_action('resource_view_delete')(
                                    context, {"id": view.get('id')})
                                if verbose:
                                    click.echo("%s/%s -- Deleted datatables_view %s "
                                               "from Invalid Resource %s" % (
                                                   status, max, view.get('id'), id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to set datastore_active flag '
                                 'for Invalid Resource %s with errors:\n\n%s' % (
                                     id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_set and not list:
        _success_message('Set datastore_active flag '
                         'for %s Invalid Resources.' % len(resource_ids_to_set))
    elif not resource_ids_to_set:
        _success_message('There are no Invalid Resources '
                         'that have the datastore_active flag at this time.')


@canada.command(
    short_help="Re-submits valid DataStore Resources to Validation OR Xloader.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to re-submit to Validation. Defaults to None.')
@click.option('-e', '--empty-only', is_flag=True,
              type=click.BOOL, help='Only re-submit empty DataStore Resources.')
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True,
              type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True,
              type=click.BOOL, help='List the Resource IDs instead '
                                    'of submitting them to Validation.')
@click.option('-x', '--xloader', is_flag=True,
              type=click.BOOL,
              help='Submits the resources to Xloader instead of Validation. '
                   'Will Xloader even if file hash has not changed.')
@click.option('-f', '--failed', is_flag=True, type=click.BOOL,
              help='Only re-submit resources that failed. '
                   'Mutually exclusive with --empty-only.')
@click.option('-s', '--sync', is_flag=True, type=click.BOOL,
              help='Run validation jobs in sync mode.')
@click.option('-i', '--skip-xloader', is_flag=True, type=click.BOOL,
              help='Skip submitting to Xloader after Validation.')
def resubmit_datastore_resources(resource_id: Optional[str] = None,
                                 empty_only: Optional[bool] = False,
                                 verbose: Optional[bool] = False,
                                 quiet: Optional[bool] = False,
                                 list: Optional[bool] = False,
                                 xloader: Optional[bool] = False,
                                 failed: Optional[bool] = False,
                                 sync: Optional[bool] = False,
                                 skip_xloader: Optional[bool] = False):
    """
    Re-submits valid DataStore Resources to Validation OR Xloader (use --xloader).
    """

    try:
        get_action('resource_validation_run')
    except Exception:
        _error_message("Validation extension is not active.")
        return
    try:
        get_action('xloader_submit')
    except Exception:
        _error_message("Xloader extension is not active.")
        return

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_submit = []
    status = 1
    if not resource_id:
        # gets valid Resources, w/ datastore_active=1
        resource_ids = _get_datastore_resources(verbose=verbose)
        max = len(resource_ids)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_submit:
                continue
            if resource_id in datastore_tables:
                try:
                    if empty_only:
                        count = _get_datastore_count(
                            context, resource_id, verbose=verbose,
                            status=status, max=max)
                        if int(count) == 0:
                            if verbose:
                                click.echo("%s/%s -- Resource %s has %s rows in "
                                           "DataStore. Let's fix this one..." % (
                                               status, max, resource_id, count))
                            resource_ids_to_submit.append(resource_id)
                        elif verbose:
                            click.echo("%s/%s -- Resource %s has %s "
                                       "rows in DataStore. Skipping..." % (
                                           status, max, resource_id, count))
                    elif failed:
                        if xloader:
                            # check xloader status
                            try:
                                xloader_job = get_action('xloader_status')(
                                    {'ignore_auth': True}, {'resource_id': resource_id})
                            except Exception as e:
                                if verbose:
                                    errors.write('Failed to get XLoader Report '
                                                 'for Resource %s with errors:\n\n%s' %
                                                 (resource_id, e))
                                    errors.write('\n')
                                    traceback.print_exc(file=errors)
                                xloader_job = {}
                                pass
                            if xloader_job.get('status') == 'error':
                                resource_ids_to_submit.append(resource_id)
                                if verbose:
                                    click.echo("%s/%s -- Going to re-submit "
                                               "Resource %s..." % (
                                                   status, max, resource_id))
                            elif verbose:
                                click.echo("%s/%s -- Resource %s did "
                                           "not fail XLoader. Skipping..." % (
                                               status, max, resource_id))
                        else:
                            # check validation status
                            try:
                                res_dict = get_action('resource_show')(
                                    {'ignore_auth': True}, {'id': resource_id})
                            except Exception as e:
                                if verbose:
                                    errors.write('Failed to get Resource %s '
                                                 'with errors:\n\n%s' % (
                                                     resource_id, e))
                                    errors.write('\n')
                                    traceback.print_exc(file=errors)
                                res_dict = {}
                                pass
                            if res_dict.get('validation_status') == 'failure':
                                resource_ids_to_submit.append(resource_id)
                                if verbose:
                                    click.echo("%s/%s -- Going to re-submit "
                                               "Resource %s..." % (
                                                   status, max, resource_id))
                            elif verbose:
                                click.echo("%s/%s -- Resource %s did not fail "
                                           "Validation. Skipping..." % (
                                               status, max, resource_id))
                    else:
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("%s/%s -- Going to re-submit "
                                       "Resource %s..." % (
                                           status, max, resource_id))
                except Exception as e:
                    if verbose:
                        errors.write('Failed to get DataStore info '
                                     'for Resource %s with errors:\n\n%s' % (
                                         resource_id, e))
                        errors.write('\n')
                        traceback.print_exc(file=errors)
                    pass
            status += 1
    else:
        # we want to check that the provided resource id has no DataStore rows still
        try:
            if empty_only:
                count = _get_datastore_count(context, resource_id, verbose=verbose)
                if int(count) == 0:
                    if verbose:
                        click.echo("1/1 -- Resource %s has %s rows "
                                   "in DataStore. Let's fix this one..." % (
                                       resource_id, count))
                    resource_ids_to_submit.append(resource_id)
                elif verbose:
                    click.echo("1/1 -- Resource %s has %s rows "
                               "in DataStore. Skipping..." % (
                                   resource_id, count))
            elif failed:
                if xloader:
                    # check xloader status
                    try:
                        xloader_job = get_action('xloader_status')(
                            {'ignore_auth': True}, {'resource_id': resource_id})
                    except Exception as e:
                        if verbose:
                            errors.write('Failed to get XLoader Report for '
                                         'Resource %s with errors:\n\n%s' % (
                                             resource_id, e))
                            errors.write('\n')
                            traceback.print_exc(file=errors)
                        xloader_job = {}
                        pass
                    if xloader_job.get('status') == 'error':
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("1/1 -- Going to re-submit "
                                       "Resource %s..." % (resource_id))
                    elif verbose:
                        click.echo("1/1 -- Resource %s did not fail "
                                   "XLoader. Skipping..." % (resource_id))
                else:
                    # check validation status
                    try:
                        res_dict = get_action('resource_show')(
                            {'ignore_auth': True}, {'id': resource_id})
                    except Exception as e:
                        if verbose:
                            errors.write('Failed to get Resource %s '
                                         'with errors:\n\n%s' % (resource_id, e))
                            errors.write('\n')
                            traceback.print_exc(file=errors)
                        res_dict = {}
                        pass
                    if res_dict.get('validation_status') == 'failure':
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("1/1 -- Going to re-submit "
                                       "Resource %s..." % (resource_id))
                    elif verbose:
                        click.echo("1/1 -- Resource %s did not fail "
                                   "Validation. Skipping..." % (resource_id))
            else:
                resource_ids_to_submit.append(resource_id)
                if verbose:
                    click.echo("1/1 -- Going to re-submit "
                               "Resource %s..." % (resource_id))
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info for '
                             'Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_submit and not quiet and not list:
        if xloader:
            click.confirm("Do you want to re-submit %s "
                          "Resources to Xloader?" %
                          len(resource_ids_to_submit), abort=True)
        else:
            click.confirm("Do you want to re-submit %s "
                          "Resources to Validation?" %
                          len(resource_ids_to_submit), abort=True)

    status = 1
    max = len(resource_ids_to_submit)
    async_mode = False if sync else True
    for id in resource_ids_to_submit:
        if list:
            click.echo(id)
        else:
            try:
                if xloader:
                    get_action('xloader_submit')(
                        context, {"resource_id": id, "ignore_hash": True})
                    msg = "%s/%s -- Submitted Resource %s "\
                          "to Xloader" % (status, max, id)
                else:
                    get_action('resource_validation_run')(
                        context, {"resource_id": id, "async": async_mode,
                                  "skip_xloader": skip_xloader})
                    if async_mode:
                        msg = "%s/%s -- Submitted Resource %s "\
                              "to Validation" % (status, max, id)
                    else:
                        msg = "%s/%s -- Ran Resource %s "\
                              "through Validation" % (status, max, id)
                if verbose:
                    click.echo(msg)
            except Exception as e:
                if verbose:
                    if xloader:
                        errors.write('Failed to submit Resource %s '
                                     'to Xloader with errors:\n\n%s' % (id, e))
                    else:
                        if async_mode:
                            errors.write('Failed to submit Resource %s '
                                         'to Validation with errors:\n\n%s' % (id, e))
                        else:
                            errors.write('Failed to run Resource %s '
                                         'through Validation with errors:\n\n%s' % (
                                             id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_submit and not list:
        if xloader:
            _success_message('Re-submitted %s Resources '
                             'to Xloader.' % len(resource_ids_to_submit))
        else:
            if async_mode:
                _success_message('Re-submitted %s Resources '
                                 'to Validation.' % len(resource_ids_to_submit))
            else:
                _success_message('Ran %s Resources '
                                 'through Validation.' % len(resource_ids_to_submit))
    elif not resource_ids_to_submit:
        _success_message('No valid, empty DataStore Resources '
                         'to re-submit at this time.')


@canada.command(short_help="Deletes Invalid Resource DataStore tables.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to delete the DataStore table for. Defaults to None.')
@click.option('-d', '--delete-table-views', is_flag=True,
              type=click.BOOL, help='Deletes any Datatable Views from the Resource.')
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True,
              type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True,
              type=click.BOOL,
              help='List the Resource IDs instead of deleting their DataStore tables.')
@click.option('-e', '--any-empty', is_flag=True,
              type=click.BOOL,
              help='Deletes any empty DataStore tables, valid or invalid Resources.')
def delete_invalid_datastore_tables(resource_id: Optional[str] = None,
                                    delete_table_views: Optional[bool] = False,
                                    verbose: Optional[bool] = False,
                                    quiet: Optional[bool] = False,
                                    list: Optional[bool] = False,
                                    any_empty: Optional[bool] = False):
    """
    Deletes Invalid Resources DataStore tables. Even if the table is not empty.
    """

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_delete = []
    if not resource_id:
        get_valid = False
        if any_empty:
            get_valid = None  # will get valid and invalid Resources
        # w/ datastore_active=1
        resource_ids = _get_datastore_resources(valid=get_valid, verbose=verbose)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_delete:
                continue
            if resource_id in datastore_tables:
                resource_ids_to_delete.append(resource_id)
    else:
        resource_ids_to_delete.append(resource_id)

    if resource_ids_to_delete and not quiet and not list:
        click.confirm("Do you want to delete the "
                      "DataStore tables for %s Resources?" %
                      len(resource_ids_to_delete), abort=True)

    status = 1
    max = len(resource_ids_to_delete)
    for id in resource_ids_to_delete:
        if list:
            click.echo(id)
        else:
            try:
                get_action('datastore_delete')(
                    context, {"resource_id": id, "force": True})
                if verbose:
                    click.echo("%s/%s -- Deleted DataStore "
                               "table for Resource %s" % (status, max, id))
                if delete_table_views:
                    views = get_action('resource_view_list')(context, {"id": id})
                    if views:
                        for view in views:
                            if view.get('view_type') == 'datatables_view':
                                get_action('resource_view_delete')(
                                    context, {"id": view.get('id')})
                                if verbose:
                                    click.echo("%s/%s -- Deleted datatables_view %s "
                                               "from Invalid Resource %s" % (
                                                   status, max, view.get('id'), id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to delete DataStore '
                                 'table for Resource %s with errors:\n\n%s' % (id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_delete and not list:
        _success_message('Deleted %s DataStore tables.' % len(resource_ids_to_delete))
    elif not resource_ids_to_delete:
        _success_message('No Invalid Resources at this time.')


@canada.command(short_help="Deletes all datatable views from non-datastore Resources.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to delete the table views for. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True,
              type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True,
              type=click.BOOL,
              help='List the Resource IDs instead of deleting their table views.')
def delete_table_view_from_non_datastore_resources(
        resource_id: Optional[str] = None,
        verbose: Optional[bool] = False,
        quiet: Optional[bool] = False,
        list: Optional[bool] = False):
    """
    Deletes all datatable views from Resources that are not datastore_active.
    """

    errors = StringIO()

    context = _get_site_user_context()

    view_ids_to_delete = []
    if not resource_id:
        # gets invalid and valid Resources, w/ datastore_active=1|0
        resource_ids = _get_datastore_resources(
            valid=None, is_datastore_active=False, verbose=verbose)
        for resource_id in resource_ids:
            try:
                views = get_action('resource_view_list')(
                    context, {"id": resource_id})
                if views:
                    for view in views:
                        if view.get('view_type') == 'datatables_view':
                            if view.get('id') in view_ids_to_delete:
                                continue
                            if verbose:
                                click.echo("Resource %s has datatables_view %s. "
                                           "Let's delete this one..." % (
                                               resource_id, view.get('id')))
                            view_ids_to_delete.append(view.get('id'))
                elif verbose:
                    click.echo("Resource %s has no views. "
                               "Skipping..." % (resource_id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to get views for Resource %s '
                                 'with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
    else:
        try:
            status = 1
            views = get_action('resource_view_list')(
                context, {"id": resource_id})
            max = len(views)
            if views:
                for view in views:
                    if view.get('view_type') == 'datatables_view':
                        if view.get('id') in view_ids_to_delete:
                            continue
                        if verbose:
                            click.echo("%s/%s -- Resource %s has datatables_view %s. "
                                       "Let's delete this one..." % (
                                           status, max, resource_id, view.get('id')))
                        view_ids_to_delete.append(view.get('id'))
                        status += 1
            elif verbose:
                status = 1
                max = 1
                click.echo("%s/%s -- Resource %s has no datatables_view(s). "
                           "Skipping..." % (status, max, resource_id))
        except Exception as e:
            if verbose:
                errors.write('Failed to get views for Resource %s '
                             'with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if view_ids_to_delete and not quiet and not list:
        click.confirm("Do you want to delete %s "
                      "datatables_view(s)?" %
                      len(view_ids_to_delete), abort=True)

    status = 1
    max = len(view_ids_to_delete)
    for id in view_ids_to_delete:
        if list:
            click.echo(id)
        else:
            try:
                get_action('resource_view_delete')(
                    context, {"id": id})
                if verbose:
                    click.echo("%s/%s -- Deleted datatables_view %s" % (
                        status, max, id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to delete datatables_view %s '
                                 'with errors:\n\n%s' % (id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif view_ids_to_delete and not list:
        _success_message('Deleted %s datatables_view(s).' % len(view_ids_to_delete))
    elif not view_ids_to_delete:
        _success_message('No datatables_view(s) at this time.')


@db.command("resolve_duplicate_emails",
            short_help="Resolve duplicate emails by "
                       "deactivating all but the first created user.")
@click.option("-q", "--quiet", is_flag=True,
              help="Suppress human interaction.", default=False)
@click.option("-v", "--verbose", is_flag=True,
              help="Increase verbosity", default=False)
def resolve_duplicate_emails(quiet: Optional[bool] = False,
                             verbose: Optional[bool] = False):
    """
    Resolve duplicate emails by deactivating all but the first created user.
    """

    q = model.Session.query(model.User.email,
                            model.User.name,
                            model.User.created) \
        .filter(model.User.state == "active") \
        .filter(model.User.email != "") \
        .order_by(model.User.email).all()

    duplicates_found = False
    users_to_delete = []
    try:
        for _k, grp in groupby(q, lambda x: x[0]):
            users = [(user[1], user[2]) for user in grp]
            _users = sorted(users, key=lambda x: x[1])
            if len(users) > 1:
                duplicates_found = True
                _users = sorted(users, key=lambda x: x[1])
                if verbose:
                    click.echo('\n- Going to keep user %s' % _users[0][0])
                for user, _created in _users[1:]:
                    if user not in users_to_delete:
                        if verbose:
                            click.echo('- Going to deactivate user %s' % user)
                        users_to_delete.append(user)
                if verbose:
                    click.echo('\n')
    except Exception as e:
        _error_message(str(e))
        return
    if users_to_delete:
        if not quiet:
            click.confirm("\nAre you sure you want to "
                          "deactivate {num} duplicate users?".format(
                              num=len(users_to_delete)), abort=True)
        for user in users_to_delete:
            try:
                get_action('user_delete')({'ignore_auth': True}, {'id': user})
                if verbose:
                    click.echo('- Deactivated user %s' % user)
            except Exception as e:
                if verbose:
                    _error_message(str(e))

        click.echo("\nDeactivated {num} duplicate "
                   "users".format(num=len(users_to_delete)))
    if not duplicates_found:
        _success_message('No duplicate emails found')


@canada.command(short_help="Generates the report for dataset Opennes Ratings.")
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
@click.option('-d', '--details', is_flag=True,
              type=click.BOOL, help='Include more dataset details.')
@click.option('-D', '--dump', type=click.File('w'),
              help='Dump results to a CSV file.')
@click.option('-p', '--package-id', type=click.STRING,
              default='c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7',
              help='Dataset ID, defaults to c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7')
def openness_report(
        verbose: Optional[bool] = False,
        details: Optional[bool] = False,
        dump: Optional[Union['click.File', bool]] = False,
        package_id: Optional[str] = 'c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7'):

    lc = LocalCKAN()

    try:
        package = lc.action.package_show(id=package_id)
    except NotFound:
        click.echo('Could not find dataset: %s' % package_id, err=True)
        return

    uri = None
    for res in package['resources']:
        if res['url'][-3:] == '.gz':
            uri = res['url']
            break

    if not uri:
        click.echo('Could not find GZIP resource', err=True)
        return

    if verbose:
        click.echo("Downloading records from %s" % uri)

    r = requests.get(uri, stream=True)
    zf = BytesIO(r.content)

    def iter_records() -> Generator[List[Dict[str, Any]], None, None]:
        _records = []
        try:
            with gzip.GzipFile(fileobj=zf, mode='rb') as fd:
                for line in fd:
                    _records.append(json.loads(line.decode('utf-8')))
                    if len(_records) >= 50:
                        yield (_records)
                        _records = []
            if len(_records) > 0:
                yield (_records)
        except GeneratorExit:
            pass
        except Exception:
            if verbose:
                traceback.print_exc()
            click.echo('Error reading downloaded file', err=True)

    if details:
        reports = defaultdict(list)
        for records in iter_records():
            for record in records:
                id = record['id']
                score = toolkit.h.openness_score(record)
                report = reports[record['organization']['title']]
                title = record["title_translated"]
                title = title.get('en', title.get('en-t-fr', '')) + \
                    ' | ' + title.get('fr', title.get('fr-t-en', ''))
                url = ''.join(['https://open.canada.ca/data/en/dataset/', id, ' | ',
                               'https://ouvert.canada.ca/data/fr/dataset/', id])
                report.append([title, url, score])

        if verbose:
            click.echo("Dumping detailed openness "
                       "ratings to %s" % getattr(dump, 'name', 'stdout'))

        orgs = list(reports)
        orgs.sort()
        if dump:
            outf = dump
        else:
            outf = sys.stdout
        # type_ignore_reason: incomplete click typing
        outf.write(BOM)  # type: ignore
        out = csv.writer(outf)  # type: ignore
        # Header
        out.writerow(["Department Name Englist | Nom du ministère en français",
                      "Title English | Titre en français",
                      "URL",
                      "Openness Rating | Cote d'ouverture"])
        for k in orgs:
            rlist = reports[k]
            for r in rlist:
                line = [k, r[0], r[1], r[2]]
                out.writerow(line)
        if dump:
            # type_ignore_reason: incomplete click typing
            outf.close()  # type: ignore
        if verbose:
            click.echo("Done!")
        return

    reports = defaultdict(lambda: defaultdict(int))
    for records in iter_records():
        for record in records:
            score = toolkit.h.openness_score(record)
            report = reports[record['organization']['title']]
            report[score] += 1

    if verbose:
        click.echo("Dumping openness ratings to %s" % getattr(dump, 'name', 'stdout'))
    if dump:
        outf = dump
    else:
        outf = sys.stdout
    # type_ignore_reason: incomplete click typing
    outf.write(BOM)  # type: ignore
    out = csv.writer(outf)  # type: ignore
    # Header
    out.writerow([
        "Department Name English / Nom du ministère en anglais",
        "Department Name French / Nom du ministère en français",
        "Openness report (score:count) / Rapport d'ouverture (score: compter)"])
    for k, v in reports.items():
        names = list(map(lambda x: x.strip(), k.split('|')))
        line = [names[0], names[1], dict(v)]
        out.writerow(line)
    if dump:
        # type_ignore_reason: incomplete click typing
        outf.close()  # type: ignore
    if verbose:
        click.echo("Done!")


@canada.command(short_help="Deletes old database triggers.")
@click.option('-v', '--verbose', is_flag=True,
              type=click.BOOL, help='Increase verbosity.')
def delete_old_triggers(verbose: Optional[bool] = False):
    """
    Delete old, unused database triggers.
    """
    _drop_function('no_surrounding_whitespace_error', verbose)
    _drop_function('year_optional_month_day_error', verbose)
    _drop_function('choices_from', verbose)
    _drop_function('integer_or_na_nd_error', verbose)
    _drop_function('inventory_trigger', verbose)


def _drop_function(name: str, verbose: Optional[bool] = False):
    sql = '''
        DROP FUNCTION {name};
        '''.format(name=datastore.identifier(name))

    try:
        datastore._write_engine_execute(sql)
    except datastore.ProgrammingError as pe:
        if verbose:
            click.echo('Failed to drop function: {0}\n{1}'.format(
                name, str(datastore._programming_error_summary(pe))), err=True)
        pass
