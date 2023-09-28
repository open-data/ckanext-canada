#!/usr/bin/env python
from __future__ import print_function

from docopt import docopt

from ckan.lib.cli import CkanCommand

import ckanext.canada.utils as utils
from ckanext.canada.triggers import update_triggers


#TODO: move all of this to ckanext.canda.cli and deprecate in the usage here...

USAGE = """

DEPRECATED: use `ckan [-c/--c=<config>] canada` instead.

Commands:
    - portal-update               Updates Portal records with Registry records.
    - copy-datasets               Copy records from another source.
    - changed-datasets            Lists changed records.
    - load-suggested              Load Suggested Datasets from a CSV file.
    - update-triggers             Updates/creates database triggers.
    - update-inventory-votes      Load Inventory Votes from a CSV file.
    - resource-size-update         Tries to update resource sizes from a CSV file.
    - update-resource-url-https   Tries to replace resource URLs from http to https.
    - bulk-validate               Runs ckanext-validation for all supported resources.

Usage:
    canada portal-update <portal.ini> -u <user>
                         [<last activity date> | [<k>d][<k>h][<k>m]]
                         [-p <num>] [-m] [-l <log file>]
                         [-t <num> [-d <seconds>]] [--c=<config>]
    canada copy-datasets [-m] [-o <source url>] [--c=<config>]
    canada changed-datasets [<since date>] [-s <remote server>]
                            [-b] [--c=<config>]
    canada load-suggested [--use-created-date] <suggested-datasets.csv>
                          [--c=<config>]
    canada update-triggers [--c=<config>]
    canada update-inventory-votes <votes.json> [--c=<config>]
    canada resource-size-update <resource_sizes.csv> [--c=<config>]
    canada update-resource-url-https <https_report> <https_alt_report>
                                     [--c=<config>]
    canada bulk-validate [--c=<config>]

    <last activity date> for reading activites, default: 7 days ago
    <k> number of hours/minutes/seconds in the past for reading activities
"""


class CanadaCommand(CkanCommand):
    summary = 'ckanext-canada command line utilities.'
    usage = USAGE


    def __init__(self, name):
        super(CanadaCommand, self).__init__(name)
        self.parser.add_option(
            '-p',
            '--processes',
            dest='processes',
            default=1,
            type='int',
            help='sets the number of worker processes, default: 1'
        )
        self.parser.add_option(
            '-u',
            '--ckan-user',
            dest='ckan_user',
            default=None,
            help='sets the owner of packages created, default: ckan system user'
        )
        self.parser.add_option('-l', '--log', dest='log', default=None, help='write log of actions to log filename')
        self.parser.add_option('-m', '--mirror', dest='mirror', action='store_true', help='copy all datasets, default is to treat unreleased datasets as deleted')
        self.parser.add_option(
            '-a',
            '--push-apikey',
            dest='push_apikey',
            default=None,
            help='push to <remote server> using apikey'
        )
        self.parser.add_option('-s', '--server', dest='server', default=None, help='retrieve from <remote server>')
        self.parser.add_option('-b', '--brief', dest='brief', action='store_true', help='don\'t output requested dates')
        self.parser.add_option('-t', '--tries', dest='tries', default=1, type='int', help='try <num> times, set > 1 to retry on failures, default: 1')
        self.parser.add_option('-d', '--delay', dest='delay', default=60, type='float', help='delay between retries, default: 60')
        self.parser.add_option('--portal', dest='portal', action='store_true', help='don\'t filter record types')
        self.parser.add_option('-o', '--source', dest='src_ds_url', default=None, help='source datastore url to copy datastore records')
        self.parser.add_option('--use-created-date', dest='use_created_date', action='store_true', help='use date_created field for date forwarded to data owner and other statuses instead of today\'s date')


    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        return
        self._load_config()
        args = docopt(USAGE, argv=self.args)

        if args['portal-update']:
            utils.portal_update(args[1], *args[2:])

        elif args['copy-datasets']:
            with utils._quiet_int_pipe():
                utils.copy_datasets(source=self.options.src_ds_url,
                                    user=self.options.ckan_user,
                                    mirror=self.options.mirror)

        elif args['changed-datasets']:
            utils.changed_datasets(*self.args[1:])

        elif args['update-triggers']:
            update_triggers()

        elif args['update-inventory-votes']:
            utils.update_inventory_votes(*self.args[1:])

        elif args['resource-size-update']:
            utils.resource_size_update(*self.args[1:])

        elif args['load-suggested']:
            utils.load_suggested(self.options.use_created_date, *self.args[1:])

        elif args['update-resource-url-https']:
            utils.resource_https_update(*self.args[1:])

        elif args['bulk-validate']:
            utils.bulk_validate()
