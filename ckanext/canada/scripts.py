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


def _get_datastore_resources(valid=True, is_datastore_active=True, verbose=False):
    # type: (bool, bool, bool) -> list
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
                if is_datastore_active:
                    click.echo("Looking through %s packages to find DataStore Resources." % len(_packages))
                else:
                    click.echo("Looking through %s packages to find NON-DataStore Resources." % len(_packages))
                if valid == None:
                    click.echo("Gathering Invalid and Valid Resources...")
                elif valid == True:
                    click.echo("Gathering only Valid Resources...")
                elif valid == False:
                    click.echo("Gathering only Invalid Resources...")
            counter += len(_packages)
            for _package in _packages:
                for _resource in _package.get('resources', []):
                    if _resource.get('id') in datastore_resources:  # already in return list
                        continue
                    if _resource.get('url_type') != 'upload' \
                    and _resource.get('url_type') != '':  # we only want upload or link types
                        continue
                    if is_datastore_active and not _resource.get('datastore_active'):
                        continue
                    if not is_datastore_active and _resource.get('datastore_active'):
                        continue
                    if valid == None:
                        datastore_resources.append(_resource.get('id'))
                        continue
                    validation_status = _resource.get('validation_status')
                    if valid == True and validation_status == 'success':
                        datastore_resources.append(_resource.get('id'))
                        continue
                    if valid == False and validation_status == 'failure':
                        datastore_resources.append(_resource.get('id'))
                        continue
        else:
            results = False
    if verbose:
        if is_datastore_active:
            click.echo("Gathered %s DataStore Resources." % len(datastore_resources))
        else:
            click.echo("Gathered %s NON-DataStore Resources." % len(datastore_resources))
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
@click.option('-d', '--delete-table-views', is_flag=True, type=click.BOOL, help='Deletes any Datatable Views from the Resource.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of setting the flags to false.')
def set_datastore_false_for_invalid_resources(resource_id=None, delete_table_views=False, verbose=False, quiet=False, list=False):
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
                if delete_table_views:
                    views = get_action('resource_view_list')(context, {"id": id})
                    if views:
                        for view in views:
                            if view.get('view_type') == 'datatables_view':
                                get_action('resource_view_delete')(context, {"id": view.get('id')})
                                if verbose:
                                    click.echo("%s/%s -- Deleted datatables_view %s from Invalid Resource %s" % (status, max, view.get('id'), id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to set datastore_active flag for Invalid Resource %s with errors:\n\n%s' % (id, e))
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
    elif not resource_ids_to_set:
        _success_message('There are no Invalid Resources that have the datastore_active flag at this time.')


@canada_scripts.command(short_help="Re-submits valid, empty DataStore Resources to Validation.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to re-submit to Validation. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of submitting them to Validation.')
def resubmit_empty_datastore_resources(resource_id=None, verbose=False, quiet=False, list=False):
    """
    Re-submits valid, empty DataStore Resources to Validation.
    """

    try:
        get_action('resource_validation_run')
    except Exception:
        _error_message("Validation extension is not active.")
        return

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
        click.confirm("Do you want to re-submit %s Resources to Validation?" % len(resource_ids_to_submit), abort=True)

    status = 1
    max = len(resource_ids_to_submit)
    for id in resource_ids_to_submit:
        if list:
            click.echo(id)
        else:
            try:
                get_action('resource_validation_run')(context, {"resource_id": id, "async": True})
                if verbose:
                    click.echo("%s/%s -- Submitted Resource %s to Validation" % (status, max, id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to submit Resource %s to Validation with errors:\n\n%s' % (id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
        status += 1

    has_errors = errors.tell()
    errors.seek(0)
    if has_errors:
        _error_message(errors.read())
    elif resource_ids_to_submit and not list:
        _success_message('Re-submitted %s Resources to Validation.' % len(resource_ids_to_submit))
    elif not resource_ids_to_submit:
        _success_message('No valid, empty DataStore Resources to re-submit at this time.')


@canada_scripts.command(short_help="Deletes Invalid Resource DataStore tables.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to delete the DataStore table for. Defaults to None.')
@click.option('-d', '--delete-table-views', is_flag=True, type=click.BOOL, help='Deletes any Datatable Views from the Resource.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of deleting their DataStore tables.')
def delete_invalid_datastore_tables(resource_id=None, delete_table_views=False, verbose=False, quiet=False, list=False):
    """
    Deletes Invalid Resources DataStore tables. Even if the table is not empty.
    """

    errors = StringIO()

    context = _get_site_user_context()

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_delete = []
    if not resource_id:
        resource_ids = _get_datastore_resources(valid=False, verbose=verbose)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_delete:
                continue
            if resource_id in datastore_tables:
                resource_ids_to_delete.append(resource_id)
    else:
        resource_ids_to_delete.append(resource_id)

    if resource_ids_to_delete and not quiet and not list:
        click.confirm("Do you want to delete the DataStore tables for %s Resources?" % len(resource_ids_to_delete), abort=True)

    status = 1
    max = len(resource_ids_to_delete)
    for id in resource_ids_to_delete:
        if list:
            click.echo(id)
        else:
            try:
                get_action('datastore_delete')(context, {"resource_id": id, "force": True})
                if verbose:
                    click.echo("%s/%s -- Deleted DataStore table for Resource %s" % (status, max, id))
                if delete_table_views:
                    views = get_action('resource_view_list')(context, {"id": id})
                    if views:
                        for view in views:
                            if view.get('view_type') == 'datatables_view':
                                get_action('resource_view_delete')(context, {"id": view.get('id')})
                                if verbose:
                                    click.echo("%s/%s -- Deleted datatables_view %s from Invalid Resource %s" % (status, max, view.get('id'), id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to delete DataStore table for Resource %s with errors:\n\n%s' % (id, e))
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


@canada_scripts.command(short_help="Deletes all datatable views from non-datastore Resources.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to delete the table views for. Defaults to None.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of deleting their table views.')
def delete_table_view_from_non_datastore_resources(resource_id=None, verbose=False, quiet=False, list=False):
    """
    Deletes all datatable views from Resources that are not datastore_active.
    """

    errors = StringIO()

    context = _get_site_user_context()

    view_ids_to_delete = []
    if not resource_id:
        resource_ids = _get_datastore_resources(valid=None, is_datastore_active=False, verbose=verbose)
        for resource_id in resource_ids:
            try:
                views = get_action('resource_view_list')(context, {"id": resource_id})
                if views:
                    for view in views:
                        if view.get('view_type') == 'datatables_view':
                            if view.get('id') in view_ids_to_delete:
                                continue
                            if verbose:
                                click.echo("Resource %s has datatables_view %s. Let's delete this one..." % (resource_id, view.get('id')))
                            view_ids_to_delete.append(view.get('id'))
                elif verbose:
                    click.echo("Resource %s has no views. Skipping..." % (resource_id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to get views for Resource %s with errors:\n\n%s' % (resource_id, e))
                    errors.write('\n')
                    traceback.print_exc(file=errors)
                pass
    else:
        try:
            views = get_action('resource_view_list')(context, {"id": resource_id})
            if views:
                for view in views:
                    if view.get('view_type') == 'datatables_view':
                        if view.get('id') in view_ids_to_delete:
                            continue
                        if verbose:
                            click.echo("%s/%s -- Resource %s has datatables_view %s. Let's delete this one..." % (status, max, resource_id, view.get('id')))
                        view_ids_to_delete.append(view.get('id'))
            elif verbose:
                click.echo("%s/%s -- Resource %s has no datatables_view(s). Skipping..." % (status, max, resource_id))
        except Exception as e:
            if verbose:
                errors.write('Failed to get views for Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if view_ids_to_delete and not quiet and not list:
        click.confirm("Do you want to delete %s datatables_view(s)?" % len(view_ids_to_delete), abort=True)

    status = 1
    max = len(view_ids_to_delete)
    for id in view_ids_to_delete:
        if list:
            click.echo(id)
        else:
            try:
                get_action('resource_view_delete')(context, {"id": id})
                if verbose:
                    click.echo("%s/%s -- Deleted datatables_view %s" % (status, max, id))
            except Exception as e:
                if verbose:
                    errors.write('Failed to delete datatables_view %s with errors:\n\n%s' % (id, e))
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
