import re
import csv
import json
import io
import time
import sys
import subprocess

from contextlib import contextmanager
from urllib.request import URLError
from urllib.parse import urlparse
from datetime import datetime, timedelta

import ckan.plugins.toolkit as toolkit
from ckan.logic.validators import isodate

from ckanapi.cli.workers import worker_pool
from ckanapi.cli.utils import completion_stats

import ckanext.datastore.backend.postgres as datastore
from ckanext.datastore.helpers import datastore_dictionary

from ckanapi import (
    RemoteCKAN,
    LocalCKAN,
    NotFound,
    ValidationError,
    NotAuthorized,
    CKANAPIError
)


PAST_RE = (
    r'^'
    # Days
    r'(?:(\d+)d)?'
    # Hours
    r'(?:(\d+)h)?'
    # Minutes
    r'(?:(\d+)m)?'
    r'$'
)

DATASET_TYPES = 'info', 'dataset', 'prop'

PACKAGE_TRIM_FIELDS = ['extras', 'metadata_modified', 'metadata_created',
            'revision_id', 'revision_timestamp', 'organization',
            'version', 'tracking_summary',
            'tags', # just because we don't use them
            'num_tags', 'num_resources', 'maintainer',
            'isopen', 'relationships_as_object', 'license_title',
            'license_title_fra', 'license_url_fra', 'license_url',
            'author',
            'groups', # just because we don't use them
            'relationships_as_subject', 'department_number',
            # FIXME: remove these when we can:
            'resource_type',
            # new in 2.3:
            'creator_user_id']

RESOURCE_TRIM_FIELDS = ['package_id', 'revision_id',
                'revision_timestamp', 'cache_last_updated',
                'webstore_last_updated', 'state',
                'description', 'tracking_summary', 'mimetype_inner',
                'mimetype', 'cache_url', 'created', 'webstore_url',
                'position']


class PortalUpdater(object):
    """
    Class to update Portal records with Registry ones.
    """
    def __init__(self,
                 portal_ini,
                 ckan_user,
                 last_activity_date,
                 processes,
                 mirror,
                 log,
                 tries,
                 delay):
        self.portal_ini = portal_ini
        self.ckan_user = ckan_user
        self.last_activity_date = last_activity_date
        self.processes = processes
        self.mirror = mirror
        self.log = log
        self.tries = tries
        self.delay = delay
        self._portal_update_activity_date = None
        self._portal_update_completed = False

    def portal_update(self):
        """
        Collect batches of packages modified at local CKAN since activity_date
        and apply the package updates to the portal instance for all
        packages with published_date set to any time in the past.
        """
        if self.ckan_user is None:
            raise ValueError('--ckan-user is required for portal_update')
        self._portal_update_completed = False
        self._portal_update_activity_date = self.last_activity_date
        while self.tries > 0:
            self.tries -= 1
            self._portal_update(self._portal_update_activity_date)
            if self._portal_update_completed or not self.tries:
                return
            time.sleep(self.delay)


    def _portal_update(self, activity_date):
        # determine activity date
        if activity_date:
            past = re.match(PAST_RE, activity_date)
            if past:
                days, hours, minutes = (
                    int(x) if x else 0 for x in past.groups()
                )
                activity_date = datetime.now() - timedelta(
                    days=days,
                    seconds=(hours * 60 + minutes) * 60
                )
            else:
                activity_date = isodate(activity_date, None)
        else:
            activity_date = datetime.now() - timedelta(days=7)

        log = None
        if self.log is not None:
            log = open(self.log, 'a')

        registry = LocalCKAN()
        source_ds = str(datastore.get_write_engine().url)

        def changed_package_id_runs(start_date):
            # retrieve a list of changed packages from the registry
            while True:
                packages, next_date = _changed_packages_since(
                    registry, start_date)
                if next_date is None:
                    return
                yield packages, next_date
                start_date = next_date

        # copy the changed packages to portal
        cmd = [
            sys.argv[0],
            '-c',
            self.portal_ini,
            'canada',
            'copy-datasets',
            '-o',
            source_ds,
            '-u',
            self.ckan_user
        ]
        if self.mirror:
            cmd.append('-m')

        pool = worker_pool(
            cmd,
            self.processes,
            [],
            stop_when_jobs_done=False,
            stop_on_keyboard_interrupt=False,
            )

        # Advance generator so we may call send() below
        pool.next()

        def append_log(finished, package_id, action, reason):
            if not log:
                return
            log.write(json.dumps([
                datetime.now().isoformat(),
                finished,
                package_id,
                action,
                reason,
                ]) + '\n')
            log.flush()

        with _quiet_int_pipe():
            append_log(
                None,
                None,
                "started updating from:",
                activity_date.isoformat()
            )

            for packages, next_date in (
                    changed_package_id_runs(activity_date)):
                job_ids, finished, result = pool.send(enumerate(packages))
                stats = completion_stats(self.processes)
                while result is not None:
                    package_id, action, reason = json.loads(result)
                    print(job_ids, stats.next(), finished, package_id, \
                        action, reason)
                    append_log(finished, package_id, action, reason)
                    job_ids, finished, result = pool.next()

                print(" --- next batch starting at: " + next_date.isoformat())
                append_log(
                    None,
                    None,
                    "next batch starting at:",
                    next_date.isoformat()
                )
                self._portal_update_activity_date = next_date.isoformat()
            self._portal_update_completed = True


def _changed_packages_since(registry, since_time, ids_only=False):
    """
    Query source ckan instance for packages changed since_time.
    returns (packages, next since_time to query) or (None, None)
    when no more changes are found.

    registry - LocalCKAN or RemoteCKAN instance
    since_time - local datetime to start looking for changes

    If all the package ids found were included in seen_id_set this
    function will return an empty list of package ids.  Note that
    this is different than when no more changes found and (None, None)
    is returned.
    """
    data = registry.action.changed_packages_activity_timestamp_since(
        since_time=since_time.isoformat())

    if not data:
        return None, None

    packages = []
    for result in data:
        package_id = result['package_id']
        try:
            source_package = registry.action.package_show(id=package_id)
        except NotFound:
            print(package_id + " not found in database.")
        else:
            if ids_only:
                packages.append(source_package['id'])
            else:
                source_package = get_datastore_and_views(source_package, registry)
                packages.append(json.dumps(source_package))

    if data:
        since_time = isodate(data[-1]['timestamp'], None)

    return packages, since_time


def copy_datasets(source, user, mirror=False):
    """
    A process that accepts packages on stdin which are compared
    to the local version of the same package.  The local package is
    then created, updated, deleted or left unchanged.  This process
    outputs that action as a string 'created', 'updated', 'deleted'
    or 'unchanged'
    """
    with _quiet_int_pipe():
        portal = LocalCKAN(username = user)

        now = datetime.now()

        packages = iter(sys.stdin.readline, '')
        for package in packages:
            source_pkg = json.loads(package)
            package_id = source_pkg['id']
            reason = None
            target_deleted = False
            if source_pkg and source_pkg['state'] == 'deleted':
                source_pkg = None

            if source_pkg and source_pkg['type'] not in DATASET_TYPES:
                # non-default dataset types ignored
                source_pkg = None

            _trim_package(source_pkg)

            action = None
            if source_pkg and not mirror:
                if source_pkg.get('ready_to_publish') == 'false':
                    source_pkg = None
                    reason = 'marked not ready to publish'
                elif not source_pkg.get('portal_release_date'):
                    source_pkg = None
                    reason = 'release date not set'
                elif isodate(source_pkg['portal_release_date'], None) > now:
                    source_pkg = None
                    reason = 'release date in future'
                else:
                    # portal packages published public
                    source_pkg['private'] = False

            target_pkg = None
            if action != 'skip':
                try:
                    target_pkg = portal.call_action('package_show', {
                        'id': package_id
                    })
                except (NotFound, NotAuthorized):
                    target_pkg = None
                except (CKANAPIError, URLError) as e:
                    sys.stdout.write(
                        json.dumps([
                            package_id,
                            'target error',
                            str(e.args)
                        ]) + '\n'
                    )
                    raise
                if target_pkg and target_pkg['state'] == 'deleted':
                    target_pkg = None
                    target_deleted = True

                target_pkg = get_datastore_and_views(target_pkg, portal)
                _trim_package(target_pkg)

            target_hash = {}

            if action == 'skip':
                pass
            elif target_pkg is None and source_pkg is None:
                action = 'unchanged'
                reason = reason or 'deleted on registry'
            elif target_deleted:
                action = 'updated'
                reason = 'undeleting on target'
                portal.action.package_update(**source_pkg)
                for r in source_pkg['resources']:
                    target_hash[r['id']] = r.get('hash')
                action += _add_datastore_and_views(source_pkg, portal, target_hash, source)
            elif target_pkg is None:
                action = 'created'
                portal.action.package_create(**source_pkg)
                action += _add_datastore_and_views(source_pkg, portal, target_hash, source)
            elif source_pkg is None:
                action = 'deleted'
                portal.action.package_delete(id=package_id)
            elif source_pkg == target_pkg:
                action = 'unchanged'
                reason = 'no difference found'
            else:
                action = 'updated'
                for r in target_pkg['resources']:
                    target_hash[r['id']] = r.get('hash')
                portal.action.package_update(**source_pkg)
                action += _add_datastore_and_views(source_pkg, portal, target_hash, source)

            sys.stdout.write(json.dumps([package_id, action, reason]) + '\n')
            sys.stdout.flush()


def changed_datasets(since_date, server, brief):
    """
    Produce a list of dataset ids and requested dates. Each package
    id will appear at most once, showing the activity date closest
    to since_date. Requested dates are preceeded with a "#"
    """
    since_date = isodate(since_date, None)

    if server:
        registry = RemoteCKAN(server)
    else:
        registry = LocalCKAN()

    while True:
        ids, since_date = _changed_packages_since(registry,
                                                  since_date,
                                                  ids_only=True)
        if not ids:
            return
        for i in ids:
            print(i)
        if not brief:
            print("# {0}".format(since_date.isoformat()))


def resource_size_update(size_report):
    registry = LocalCKAN()
    size_report = open(size_report, "r")
    reader = csv.DictReader(size_report)
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
        except NotFound as e:
            print("{0} dataset not found".format(uuid))
    size_report.close()


def resource_https_update(https_report, https_alt_report):
    """
    This function updates all broken http links into https links.
    https_report: the report with all of the links (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http/blob/main/orgs_http_data.json.
    https_alt_report: the report with links where alternates exist (a .json file)
    ex. https://github.com/open-data/opengov-orgs-http/blob/main/https_alternative_count.json.
    For more specifications about the files in use please visit,
    https://github.com/open-data/opengov-orgs-http.
    """
    alt_file = open(https_alt_report, "r")
    alt_data = json.load(alt_file)

    https_file = open(https_report, "r")
    data = json.load(https_file)
    log = open("error.log", "w")

    def check_https(check_url, check_org, check_data):
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
                        log.write('Url for resource %s updated %s\n'
                                    % (res['id'], https_url))
                except NotFound:
                    log.write('Resource %s not found\n' % res['id'])
                except ValidationError as e:
                    log.write('Resource %s failed validation %s\n'
                                % (res['id'], str(e.error_dict)))
    log.close()


def load_suggested(use_created_date, filename):
    """
    A process that loads suggested datasets from Drupal into CKAN
    """
    registry = LocalCKAN()

    # load packages as dict
    results = True
    counter = 0
    batch_size = 100
    existing_suggestions = {}
    while results:
        packages = registry.action.package_search(q='type:prop',
                                                  start=counter,
                                                  rows=batch_size,
                                                  include_private=True)['results']
        if packages:
            for package in packages:
                existing_suggestions[package['id']] = package
            counter += len(packages)
        else:
            results = False

    # load data from csv
    csv_file = io.open(filename, "r", encoding='utf-8-sig')
    csv_reader = csv.DictReader((l.encode('utf-8') for l in csv_file))
    today = datetime.now().strftime('%Y-%m-%d')

    for row in csv_reader:
        uuid = row['uuid']

        if use_created_date:
            today = row['date_created']

        # add record
        record = {
            "type": "prop",
            "state": "active",
            "id": uuid,
            "title_translated": {
                u'en': str(row['title_en'], 'utf-8'),
                u'fr': str(row['title_fr'], 'utf-8')
            },
            "owner_org": row['organization'],
            "notes_translated": {
                u'en': str(row['description_en'], 'utf-8'),
                u'fr': str(row['description_fr'], 'utf-8')
            },
            "comments": {
                u'en': str(row['additional_comments_and_feedback_en'], 'utf-8'),
                u'fr': str(row['additional_comments_and_feedback_fr'], 'utf-8')
            },
            "reason": row['reason'],
            "subject": row['subject'].split(',') if row['subject'] else ['information_and_communications'],
            "keywords": {
                u'en': str(row['keywords_en'], 'utf-8').split(',') if row['keywords_en'] else [u'dataset'],
                u'fr': str(row['keywords_fr'], 'utf-8').split(',') if row['keywords_fr'] else [u'Jeu de données'],
            },
            "date_submitted": row['date_created'],
            "date_forwarded": today,
            "status": [] if row['dataset_suggestion_status'] == 'department_contacted' else [
                {
                    "reason": row['dataset_suggestion_status'],
                    "date": row['dataset_released_date'] if row['dataset_released_date'] else today,
                    "comments": {
                        u'en': str(row['dataset_suggestion_status_link'], 'utf-8') or u'Status imported from previous ‘suggest a dataset’ system',
                        u'fr': str(row['dataset_suggestion_status_link'], 'utf-8') or u'État importé du système précédent « Proposez un jeu de données »',
                    }
                }
            ]
        }

        if uuid in existing_suggestions:
            need_patch = None
            # compare record
            for key in record:
                if record[key] and key not in ['status', 'date_forwarded']:
                    existing_value = existing_suggestions[uuid][key]
                    if key == 'owner_org':
                        existing_value = existing_suggestions[uuid]['organization']['name']
                    if record[key] != existing_value:
                        need_patch = True
                        break

            # patch if needed
            if need_patch:
                record['date_forwarded'] = existing_suggestions[uuid]['date_forwarded']
                record['status'] = existing_suggestions[uuid]['status'] \
                    if existing_suggestions[uuid].get('status') \
                    else record['status']
                if record['owner_org'] != existing_suggestions[uuid]['organization']['name']:
                    existing_org = existing_suggestions[uuid]['organization']['title'].split(' | ')
                    updated_status = {
                        "reason": 'transferred',
                        "date": today,
                        "comments": {
                            u'en': u'This suggestion is transferred from ' + existing_org[0],
                            u'fr': u'Cette proposition a été transférée de la part de ' + existing_org[1]
                        }
                    }
                    record['status'].append(updated_status)

                try:
                    registry.action.package_patch(**record)
                    print(uuid + ' suggested dataset patched')
                except ValidationError as e:
                    print(uuid + ' suggested dataset cannot be patched ' + str(e))

        else:
            try:
                registry.action.package_create(**record)
                print(uuid + ' suggested dataset created')
            except ValidationError as e:
                if 'id' in e.error_dict:
                    try:
                        registry.action.package_update(**record)
                        print(uuid + ' suggested dataset update deleted')
                    except ValidationError as e:
                        print(uuid + ' (update deleted) ' + str(e))
                else:
                    print(uuid + ' ' + str(e))
    csv_file.close()


def bulk_validate():
    """
    Usage: ckanapi search datasets include_private=true -c $CONFIG_INI |
    paster canada bulk-validate -c $CONFIG_INI

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
                        toolkit.get_action(u'datastore_search')(
                            {}, {'resource_id': resource['id']})
                        toolkit.get_action(u'datastore_delete')(
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
                        toolkit.get_action(u'resource_validation_run')(
                            {}, {'resource_id': resource['id'],
                                    'async': True,
                                    'ignore_auth': True})
                        validation_queue += 1
                        log.write("\nResource %s sent to the validation "
                                    "queue" %
                                    resource['id'])
                    except NotFound:
                        log.write("\n[ERROR]: Unable to send resource %s "
                                    "to validation queue - Resource not "
                                    "found" % resource['id'])

    log.write("\n\nTotal resources removed from datastore: " +
                str(datastore_removed))
    log.write("\nTotal resources sent to validation queue: " +
                str(validation_queue))

    log.close()


def _trim_package(pkg):
    """
    remove keys from pkg that we don't care about when comparing
    or updating/creating packages.  Also try to convert types and
    create missing fields that will be present in package_show.
    """
    # XXX full of custom hacks and deep knowledge of our schema :-(
    if not pkg:
        return
    for k in PACKAGE_TRIM_FIELDS:
        if k in pkg:
            del pkg[k]
    for r in pkg['resources']:
        for k in RESOURCE_TRIM_FIELDS:
            if k in r:
                del r[k]
        if 'datastore_contains_all_records_of_source_file' in r:
            r['datastore_contains_all_records_of_source_file'] = \
                toolkit.asbool(r['datastore_contains_all_records_of_source_file'])
        if r.get('url_type') == 'upload' and r['url']:
            r['url'] = r['url'].rsplit('/', 1)[-1]
        for k in ['name', 'size']:
            if k not in r:
                r[k] = None
    if 'name' not in pkg or not pkg['name']:
        pkg['name'] = pkg['id']
    if 'type' not in pkg:
        pkg['type'] = 'dataset'
    if 'state' not in pkg:
        pkg['state'] = 'active'
    for k in ['url']:
        if k not in pkg:
            pkg[k] = ''


def _add_datastore_and_views(package, portal, res_hash, ds):
    # create datastore table and views for each resource of the package
    action = ''
    for resource in package['resources']:
        res_id = resource['id']
        if res_id in package.keys():
            if 'data_dict' in package[res_id].keys():
                action += _add_to_datastore(portal, resource, package[res_id], res_hash, ds)
            if 'views' in package[res_id].keys():
                action += _add_views(portal, resource, package[res_id])
    return action


def _delete_datastore_and_views(package, portal):
    # remove datastore table and views for each resource of the package
    action = ''
    for resource in package['resources']:
        res_id = resource['id']
        try:
            portal.call_action('datastore_delete', {"id": resource['id'], "force": True})
            action += '\n  datastore-deleted for ' + resource['id']
        except NotFound:
            action += '\n  failed to delete datastore for ' + resource['id']
        try:
            portal.call_action('resource_view_clear', {"id": resource['id'], "force": True})
            action += '\n  views-deleted for ' + resource['id']
        except NotFound:
            action += '\n  failed to delete all views for ' + resource['id']
    return action


def _add_to_datastore(portal, resource, resource_details, t_hash, source_ds_url):
    action = ''
    try:
        portal.call_action('datastore_search', {'id': resource['id'], 'limit': 0})
        if t_hash.get(resource['id']) \
                and t_hash.get(resource['id']) == resource.get('hash')\
                and datastore_dictionary(resource['id']) == resource_details['data_dict']:
            return action
        else:
            portal.call_action('datastore_delete', {"id": resource['id'], "force": True})
            action += '\n  datastore-deleted for ' + resource['id']
    except NotFound:
        # not an issue, resource does not exist in datastore
        pass

    portal.call_action('datastore_create',
                       {"resource_id": resource['id'],
                        "fields": resource_details['data_dict'],
                        "force": True})

    action += '\n  datastore-created for ' + resource['id']

    # load data
    target_ds_url = str(datastore.get_write_engine().url)
    cmd1 = subprocess.Popen(['pg_dump', source_ds_url, '-a', '-t', resource['id']], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['psql', target_ds_url], stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = cmd2.communicate()
    action += ' data-loaded' if not result[1] else ' data-load-failed'
    return action


def _add_views(portal, resource, resource_details):
    action = ''
    target_views = portal.call_action('resource_view_list', {'id': resource['id']})
    for src_view in resource_details['views']:
        view_action = 'resource_view_create'
        for target_view in target_views:
            if target_view['id'] == src_view['id']:
                view_action = None if target_view == src_view else 'resource_view_update'

        if view_action:
            try:
                portal.call_action(view_action, src_view)
                action += '\n  ' + view_action + ' ' + src_view['id'] + ' for resource ' + resource['id']
            except ValidationError as e:
                action += '\n  ' + view_action + ' failed for view ' + src_view['id'] + ' for resource ' + resource['id']
                pass

    for target_view in target_views:
        to_delete = True
        for src_view in resource_details['views']:
            if target_view['id'] == src_view['id']:
                to_delete = False
                break
        if to_delete:
            view_action = 'resource_view_delete'
            portal.call_action(view_action, {'id':target_view['id']})
            action += '\n  ' + view_action + ' ' + src_view['id'] + ' for resource ' + resource['id']

    return action


def get_datastore_and_views(package, ckan_instance):
    if package and 'resources' in package:
        for resource in package['resources']:
            # check if resource exists in datastore
            if resource['datastore_active']:
                try:
                    table = ckan_instance.call_action('datastore_search',
                                                             {'id': resource['id'],
                                                              'limit': 0})
                    if table:
                        # add hash, views and data dictionary
                        package[resource['id']] = {
                            "hash": resource.get('hash'),
                            "views": ckan_instance.call_action('resource_view_list',
                                                               {'id': resource['id']}),
                            "data_dict": datastore_dictionary(resource['id']),
                        }
                except NotFound:
                    pass
            else:
                resource_views = ckan_instance.call_action('resource_view_list',
                                                           {'id': resource['id']})
                if resource_views:
                    package[resource['id']] = {
                        "views": resource_views}
    return package


def update_inventory_votes(json_name):
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


@contextmanager
def _quiet_int_pipe():
    """
    let pipe errors and KeyboardIterrupt exceptions cause silent exit
    """
    try:
        yield
    except KeyboardInterrupt:
        pass
    except IOError as e:
        if e.errno != 32:
            raise
