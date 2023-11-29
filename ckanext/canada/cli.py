import click
import traceback
from io import StringIO

from ckan.logic import get_action
from ckan import model

from ckanext.canada import utils, triggers


def _get_user(user):
    if user is not None:
        return user
    return get_action('get_site_user')({'ignore_auth': True}).get('name')


def get_commands():
    return canada


@click.group(short_help="Canada management commands")
def canada():
    """Canada management commands.
    """
    pass


@canada.command(short_help="Updates Portal records with Registry records.")
@click.argument("portal_ini")
@click.option(
    "-u",
    "--ckan-user",
    default=None,
    help="Sets the owner of packages created, default: ckan system user",
)
@click.argument("last_activity_date", required=False)
@click.option(
    "-p",
    "--processes",
    default=1,
    help="Sets the number of worker processes, default: 1",
)
@click.option(
    "-m",
    "--mirror",
    is_flag=True,
    help="Copy all datasets, default is to treat unreleased datasets as deleted",
)
@click.option(
    "-l",
    "--log",
    default=None,
    help="Write log of actions to log filename",
)
@click.option(
    "-t",
    "--tries",
    default=1,
    help="Try <num> times, set > 1 to retry on failures, default: 1",
)
@click.option(
    "-d",
    "--delay",
    default=60,
    help="Delay between retries, default: 60",
)
def portal_update(portal_ini,
                  ckan_user,
                  last_activity_date=None,
                  processes=1,
                  mirror=False,
                  log=None,
                  tries=1,
                  delay=60):
    """
    Collect batches of packages modified at local CKAN since activity_date
    and apply the package updates to the portal instance for all
    packages with published_date set to any time in the past.

    Full Usage:\n
        canada portal-update <portal.ini> -u <user>\n
                             [<last activity date> | [<k>d][<k>h][<k>m]]\n
                             [-p <num>] [-m] [-l <log file>]\n
                             [-t <num> [-d <seconds>]]

    <last activity date>: Last date for reading activites, default: 7 days ago\n
    <k> number of hours/minutes/seconds in the past for reading activities
    """
    utils.PortalUpdater(portal_ini,
                        ckan_user,
                        last_activity_date,
                        processes,
                        mirror,
                        log,
                        tries,
                        delay).portal_update()


@canada.command(short_help="Copy records from another source.")
@click.option(
    "-m",
    "--mirror",
    is_flag=True,
    help="Copy all datasets, default is to treat unreleased datasets as deleted",
)
@click.option(
    "-u",
    "--ckan-user",
    default=None,
    help="Sets the owner of packages created, default: ckan system user",
)
@click.option(
    "-o",
    "--source",
    default=None,
    help="Source datastore url to copy datastore records",
)
def copy_datasets(mirror=False, ckan_user=None, source=None):
    """
    A process that accepts packages on stdin which are compared
    to the local version of the same package.  The local package is
    then created, updated, deleted or left unchanged.  This process
    outputs that action as a string 'created', 'updated', 'deleted'
    or 'unchanged'

    Full Usage:\n
        canada copy-datasets [-m] [-o <source url>]
    """
    utils.copy_datasets(source,
                        _get_user(ckan_user),
                        mirror)



@canada.command(short_help="Lists changed records.")
@click.argument("since_date")
@click.option(
    "-s",
    "--server",
    default=None,
    help="Retrieve from <remote server>",
)
@click.option(
    "-b",
    "--brief",
    is_flag=True,
    help="Don't output requested dates",
)
def changed_datasets(since_date, server=None, brief=False):
    """
    Produce a list of dataset ids and requested dates. Each package
    id will appear at most once, showing the activity date closest
    to since_date. Requested dates are preceeded with a "#"

    Full Usage:\n
        canada changed-datasets [<since date>] [-s <remote server>] [-b]
    """
    utils.changed_datasets(since_date,
                           server,
                           brief)


@canada.command(short_help="Load Suggested Datasets from a CSV file.")
@click.argument("suggested_datasets_csv")
@click.option(
    "--use-created-date",
    is_flag=True,
    help="Use date_created field for date forwarded to data owner and other statuses instead of today's date",
)
def load_suggested(suggested_datasets_csv, use_created_date=False):
    """
    A process that loads suggested datasets from Drupal into CKAN

    Full Usage:\n
        canada load-suggested [--use-created-date] <suggested-datasets.csv>
    """
    utils.load_suggested(use_created_date,
                         suggested_datasets_csv)


@canada.command(short_help="Updates/creates database triggers.")
def update_triggers():
    """
    Create/update triggers used by PD tables
    """
    triggers.update_triggers()


@canada.command(short_help="Load Inventory Votes from a CSV file.")
@click.argument("votes_json")
def update_inventory_votes(votes_json):
    """

    Full Usage:\n
        canada update-inventory-votes <votes.json>
    """
    utils.update_inventory_votes(votes_json)


@canada.command(short_help="Tries to update resource sizes from a CSV file.")
@click.argument("resource_sizes_csv")
def resource_size_update(resource_sizes_csv):
    """
    Tries to update resource sizes from a CSV file.

    Full Usage:\n
        canada resource-size-update <resource_sizes.csv>
    """
    utils.resource_size_update(resource_sizes_csv)


@canada.command(short_help="Tries to replace resource URLs from http to https.")
@click.argument("https_report")
@click.argument("https_alt_report")
def update_resource_url_https(https_report, https_alt_report):
    """
    This function updates all broken http links into https links.
    https_report: the report with all of the links (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http/blob/main/orgs_http_data.json.
    https_alt_report: the report with links where alternates exist (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http/blob/main/https_alternative_count.json.
    For more specifications about the files in use please visit,
    https://github.com/open-data/opengov-orgs-http.

    Full Usage:\n
        canada update-resource-url-https <https_report> <https_alt_report>
    """
    utils.resource_https_update(https_report,
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
    utils.bulk_validate()


@canada.command(short_help="Deletes rows from the activity table.")
@click.option(
    u"-d",
    u"--days",
    help=u"Number of days to go back. E.g. 120 will keep 120 days of activities. Default: 90",
    default=90
)
@click.option(u"-q", u"--quiet", is_flag=True, help=u"Suppress human interaction.", default=False)
def delete_activities(days=90, quiet=False):
    """Delete rows from the activity table past a certain number of days.
    """
    activity_count = model.Session.execute(
                        u"SELECT count(*) FROM activity "
                        "WHERE timestamp < NOW() - INTERVAL '{d} days';"
                        .format(d=days)) \
                        .fetchall()[0][0]

    if not bool(activity_count):
        click.echo(u"\nNo activities found past {d} days".format(d=days))
        return

    if not quiet:
        click.confirm(u"\nAre you sure you want to delete {num} activities?"
                          .format(num=activity_count), abort=True)

    model.Session.execute(u"DELETE FROM activity WHERE timestamp < NOW() - INTERVAL '{d} days';".format(d=days))
    model.Session.commit()

    click.echo(u"\nDeleted {num} rows from the activity table".format(num=activity_count))


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


def _error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def _success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


@canada.command(short_help="Sets datastore_active to False for Invalid Resources.")
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

    datastore_tables = _get_datastore_tables(verbose=verbose)
    resource_ids_to_set = []
    if not resource_id:
        for resource_id in _get_datastore_resources(valid=False, verbose=verbose):
            if resource_id in resource_ids_to_set:
                continue
            if resource_id in datastore_tables:
                # we do not need to check anything else here as we know
                # at this point that the resource is not valid and it
                # still has the datastore_active flag.
                resource_ids_to_set.append(resource_id)
    else:
        resource_ids_to_set = [resource_id]

    if resource_ids_to_set and not quiet and not list:
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


@canada.command(short_help="Re-submits empty DataStore Resources to Xloader.")
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
    if not resource_id:
        for resource_id in _get_datastore_resources(verbose=verbose):
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

    if resource_ids_to_submit and not quiet and not list:
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
