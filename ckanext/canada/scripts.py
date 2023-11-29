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


def _get_datastore_tables():
    # type: () -> list
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
    return [r.get('name') for r in tables.get('records', [])]


def _get_datastore_resources(valid=True):
    # type: (bool) -> list
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
    return datastore_resources


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
    not valid but are still in the DataStore database.
    """

    try:
        from ckanext.datastore.logic.action import set_datastore_active_flag
    except ImportError:
        _error_message("DataStore extension is not active.")
        return

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables()
    resource_ids_to_set = []
    if not resource_id:
        for resource_id in _get_datastore_resources(valid=False):
            if resource_id in resource_ids_to_set:
                continue
            if resource_id in datastore_tables:
                # we do not need to check anything else here as we know
                # at this point that the resource is not valid and it
                # still has the datastore_active flag.
                resource_ids_to_set.append(resource_id)
    else:
        resource_ids_to_set = [resource_id]

    if resource_ids_to_set and not quiet:
        click.confirm("Do you want to set datastore_active flag to False for %s Invalid Resources?" % len(resource_ids_to_set), abort=True)

    for id in resource_ids_to_set:
        if list:
            click.echo(id)
        else:
            try:
                set_datastore_active_flag(model, {"resource_id": id}, False)
                if verbose:
                    click.echo("Set datastore_active flag to False for Invalid Resource %s" % id)
            except Exception as e:
                if verbose:
                    errors.write('Failed to set datastore_active flag for Invalid Resource %s with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass

    if list:
        return

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_set:
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

    datastore_tables = _get_datastore_tables()
    resource_ids_to_submit = []
    if not resource_id:
        for resource_id in _get_datastore_resources():
            if resource_id in resource_ids_to_submit:
                continue
            if resource_id in datastore_tables:
                try:
                    info = get_action('datastore_info')(context, {"id": resource_id})
                    count = info.get('meta', {}).get('count')
                    if int(count) == 0:
                        resource_ids_to_submit.append(resource_id)
                except Exception as e:
                    if verbose:
                        errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                        errors.write('\n')
                        traceback.print_exc(file=errors)
                    pass
    else:
        # we want to check that the provided resource id has no DataStore rows still
        try:
            info = get_action('datastore_info')(context, {"id": resource_id})
            count = info.get('meta', {}).get('count')
            if int(count) == 0:
                resource_ids_to_submit.append(resource_id)
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_submit and not quiet:
        click.confirm("Do you want to re-submit %s Resources to Xloader?" % len(resource_ids_to_submit), abort=True)

    for id in resource_ids_to_submit:
        if list:
            click.echo(id)
        else:
            try:
                get_action('xloader_submit')(context, {"resource_id": id, "ignore_hash": False})
                if verbose:
                    click.echo("Submitted Resource %s to Xloader" % id)
            except Exception as e:
                if verbose:
                    errors.write('Failed to submit Resource %s to Xloader with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass

    if list:
        return

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_submit:
        _success_message('Re-submitted %s Resources to Xloader.' % len(resource_ids_to_submit))
    else:
        _success_message('No empty DataStore Resources to re-submit at this time.')
