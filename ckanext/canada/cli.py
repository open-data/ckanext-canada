import click

from ckan.logic import get_action

from ckanext.canada import utils, triggers


def _get_user(user):
    if user is not None:
        return user
    return get_action('get_site_user')({'ignore_auth': True}).get('name')


def get_commands():
    return [canada]


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
