import click
import traceback

from ckan import model
from ckan.plugins.toolkit import get_action

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


def get_commands():
    return canada_scripts


@click.group(short_help="Canada miscellaneous scripts.")
def canada_scripts():
    """Canada miscellaneous scripts.
    """
    pass


def _get_site_user_context():
    user = get_action('get_site_user')({'ignore_auth': True}, {})
    return {"user": user['name'], "ignore_auth": True}


def _get_datastore_tables(verbose=False):
    # type: (bool) -> list
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
        click.echo("Gathered %s table names from the DataStore." % len(tables.get('records', [])))
    return [r.get('name') for r in tables.get('records', [])]


def _get_datastore_resources(valid=True, verbose=False):
    # type: (bool, bool) -> list
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
        _packages = get_action('package_search')(_get_site_user_context(),
                                                 {"q": "*:*",
                                                  "start": counter,
                                                  "rows": batch_size,
                                                  "include_private": True})['results']
        if _packages:
            if verbose:
                click.echo("Looking through %s packages to find DataStore Resources." % len(_packages))
            counter += len(_packages)
            for _package in _packages:
                for _resource in _package.get('resources', []):
                    if not _resource.get('datastore_active') \
                    or _resource.get('url_type') != 'upload' \
                    or _resource.get('id') in datastore_resources:
                        continue
                    validation_status = _resource.get('validation_status')
                    if valid and validation_status == 'success':
                        datastore_resources.append(_resource.get('id'))
                    if not valid and validation_status == 'failure':
                        datastore_resources.append(_resource.get('id'))
        else:
            results = False
    if verbose:
        click.echo("Gathered %s DataStore Resources." % len(datastore_resources))
    return datastore_resources


def _get_datastore_count(context, resource_id, verbose=False, status=1, max=1):
    # type: (dict, str, bool, int, int) -> int|None
    """
    Returns the count of rows in the DataStore table for a given resource ID.
    """
    if verbose:
        click.echo("%s/%s -- Checking DataStore record count for Resource %s" % (status, max, resource_id))
    info = get_action('datastore_info')(context, {"id": resource_id})
    return info.get('meta', {}).get('count')


def _error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def _success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


@canada_scripts.command(short_help="Sets datastore_active to False for Invalid Resources.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to set the datastore_active flag. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of setting the flags to false.')
def set_datastore_false_for_invalid_resources(resource_id=None, verbose=False, quiet=False, list=False):
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
        resource_ids = _get_datastore_resources(valid=False, verbose=verbose)
        max = len(resource_ids)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_set:
                continue
            if resource_id in datastore_tables:
                try:
                    count = _get_datastore_count(context, resource_id, verbose=verbose, status=status, max=max)
                    if int(count) == 0:
                        if verbose:
                            click.echo("%s/%s -- Resource %s has %s rows in DataStore. Let's fix this one..." % (status, max, resource_id, count))
                        resource_ids_to_set.append(resource_id)
                    elif verbose:
                        click.echo("%s/%s -- Resource %s has %s rows in DataStore. Skipping..." % (status, max, resource_id, count))
                except Exception as e:
                    if verbose:
                        errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                        errors.write('\n')
                        traceback.print_exc(file=errors)
                    pass
            status += 1
    else:
        try:
            count = _get_datastore_count(context, resource_id, verbose=verbose)
            if int(count) == 0:
                if verbose:
                    click.echo("1/1 -- Resource %s has %s rows in DataStore. Let's fix this one..." % (resource_id, count))
                resource_ids_to_set = [resource_id]
            elif verbose:
                click.echo("1/1 -- Resource %s has %s rows in DataStore. Skipping..." % (resource_id, count))
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_set and not quiet and not list:
        click.confirm("Do you want to set datastore_active flag to False for %s Invalid Resources?" % len(resource_ids_to_set), abort=True)

    status = 1
    max = len(resource_ids_to_set)
    for id in resource_ids_to_set:
        if list:
            click.echo(id)
        else:
            try:
                set_datastore_active_flag(model, {"resource_id": id}, False)
                if verbose:
                    click.echo("%s/%s -- Set datastore_active flag to False for Invalid Resource %s" % (status, max, id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to set datastore_active flag for Invalid Resource %s with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_set and not list:
        _success_message('Set datastore_active flag for %s Invalid Resources.' % len(resource_ids_to_set))
    else:
        _success_message('There are no Invalid Resources that have the datastore_active flag at this time.')


@canada_scripts.command(short_help="Re-submits empty DataStore Resources to Xloader.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to re-submit to Xloader. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of submitting them to Xloader.')
def resubmit_empty_datastore_resources(resource_id=None, verbose=False, quiet=False, list=False):
    """
    Re-submits empty DataStore Resources to Xloader.
    """

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_submit = []
    status = 1
    if not resource_id:
        resource_ids = _get_datastore_resources(verbose=verbose)
        max = len(resource_ids)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_submit:
                continue
            if resource_id in datastore_tables:
                try:
                    count = _get_datastore_count(context, resource_id, verbose=verbose, status=status, max=max)
                    if int(count) == 0:
                        if verbose:
                            click.echo("%s/%s -- Resource %s has %s rows in DataStore. Let's fix this one..." % (status, max, resource_id, count))
                        resource_ids_to_submit.append(resource_id)
                    elif verbose:
                        click.echo("%s/%s -- Resource %s has %s rows in DataStore. Skipping..." % (status, max, resource_id, count))
                except Exception as e:
                    if verbose:
                        errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                        errors.write('\n')
                        traceback.print_exc(file=errors)
                    pass
            status += 1
    else:
        # we want to check that the provided resource id has no DataStore rows still
        try:
            count = _get_datastore_count(context, resource_id, verbose=verbose)
            if int(count) == 0:
                if verbose:
                    click.echo("1/1 -- Resource %s has %s rows in DataStore. Let's fix this one..." % (resource_id, count))
                resource_ids_to_submit.append(resource_id)
            elif verbose:
                click.echo("1/1 -- Resource %s has %s rows in DataStore. Skipping..." % (resource_id, count))
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_submit and not quiet and not list:
        click.confirm("Do you want to re-submit %s Resources to Xloader?" % len(resource_ids_to_submit), abort=True)

    status = 1
    max = len(resource_ids_to_submit)
    for id in resource_ids_to_submit:
        if list:
            click.echo(id)
        else:
            try:
                get_action('xloader_submit')(context, {"resource_id": id, "ignore_hash": False})
                if verbose:
                    click.echo("%s/%s -- Submitted Resource %s to Xloader" % (status, max, id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to submit Resource %s to Xloader with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_submit and not list:
        _success_message('Re-submitted %s Resources to Xloader.' % len(resource_ids_to_submit))
    else:
        _success_message('No empty DataStore Resources to re-submit at this time.')
