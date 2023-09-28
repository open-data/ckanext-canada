#!/usr/bin/env python
from __future__ import print_function

from docopt import docopt

from ckan.lib.cli import CkanCommand

import ckanext.canada.utils as utils
from ckanext.canada.triggers import update_triggers


#TODO: move all of this to ckanext.canda.cli and deprecate in the usage here...

USAGE = """DEPRECATED: use `ckan [-c/--c=<config>] canada` instead.
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

Options:
    -a/--push-apikey <apikey>   push to <remote server> using apikey
    -b/--brief                  don't output requested dates
    -c/--config <ckan config>   use named ckan config file
                                (available to all commands)
    -d/--delay <seconds>        delay between retries, default: 60
    -l/--log <log filename>     write log of actions to log filename
    -m/--mirror                 copy all datasets, default is to treat
                                unreleased datasets as deleted
    -p/--processes <num>        sets the number of worker processes,
                                default: 1
    --portal                    don't filter record types
    -s/--server <remote server> retrieve from <remote server>
    -t/--tries <num>            try <num> times, set > 1 to retry on
                                failures, default: 1
    -u/--ckan-user <username>   sets the owner of packages created,
                                default: ckan system user
    --use-created-date          use date_created field for date forwarded to data
                                owner and other statuses instead of today's date
    -o/--source <source url>    source datastore url to copy datastore records
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
            type='int'
        )
        self.parser.add_option(
            '-u',
            '--ckan-user',
            dest='ckan_user',
            default=None
        )
        self.parser.add_option('-l', '--log', dest='log', default=None)
        self.parser.add_option('-m', '--mirror', dest='mirror', action='store_true')
        self.parser.add_option(
            '-a',
            '--push-apikey',
            dest='push_apikey',
            default=None
        )
        self.parser.add_option('-s', '--server', dest='server', default=None)
        self.parser.add_option('-b', '--brief', dest='brief', action='store_true')
        self.parser.add_option('-t', '--tries', dest='tries', default=1, type='int')
        self.parser.add_option('-d', '--delay', dest='delay', default=60, type='float')
        self.parser.add_option('--portal', dest='portal', action='store_true')
        self.parser.add_option('-o', '--source', dest='src_ds_url', default=None)
        self.parser.add_option('--use-created-date', dest='use_created_date', action='store_true')


    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        self._load_config()
        args = docopt(USAGE, argv=self.args)

        if not args or args['--help'] or args['-h'] or args['help']:
            print(self.usage)
            return

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

        else:
            print(self.usage)
