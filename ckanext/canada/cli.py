import re
import csv
import json
import io
import time
import sys
import subprocess
import click
import traceback
from io import StringIO, BytesIO
import gzip
import requests
from collections import defaultdict

from typing import Optional, Union, Tuple

from contextlib import contextmanager
from urllib.request import URLError
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone

from ckan.logic import get_action
from ckan import model

from ckanapi import (
    RemoteCKAN,
    LocalCKAN,
    NotFound,
    ValidationError,
    NotAuthorized,
    CKANAPIError
)

import ckan.plugins.toolkit as toolkit
from ckan.logic.validators import isodate

from ckanapi.cli.workers import worker_pool
from ckanapi.cli.utils import completion_stats

import ckanext.datastore.backend.postgres as datastore

from ckanext.canada import triggers
from ckanext.canada import model as canada_model

BOM = "\N{bom}"

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
                'position', 'metadata_modified']


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
                 delay,
                 verbose):
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
        self.verbose = verbose

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
        source_datastore_uri = str(datastore.get_write_engine().url)

        def changed_package_id_runs(start_date, verbose:Optional[bool]=False):
            # retrieve a list of changed packages from the registry
            while True:
                packages, next_date = _changed_packages_since(
                    registry, start_date, verbose=verbose)
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
            source_datastore_uri,
            '-u',
            self.ckan_user
        ]
        if self.mirror:
            cmd.append('-m')
        if self.verbose:
            cmd.append('-v')

        pool = worker_pool(
            cmd,
            self.processes,
            [],
            stop_when_jobs_done=False,
            stop_on_keyboard_interrupt=False,
            )

        # Advance generator so we may call send() below
        next(pool)

        def append_log(finished, package_id, action, reason, error: Optional[Union[str, None]]=None):
            if not log:
                return
            log.write(json.dumps([
                datetime.now().isoformat(),
                finished,
                package_id,
                action,
                reason,
                ]) + '\n')
            if error:
                log.write(error + '\n')
            log.flush()

        with _quiet_int_pipe():
            append_log(
                None,
                None,
                "started updating from:",
                activity_date.isoformat()
            )

            for packages, next_date in (
                    changed_package_id_runs(activity_date, verbose=self.verbose)):
                job_ids, finished, result = pool.send(enumerate(packages))
                stats = completion_stats(self.processes)
                while result is not None:
                    try:
                        package_id, action, reason, error, failure_reason, failure_trace, do_update_sync_success_time = json.loads(result)
                    except Exception as e:
                        if self.verbose:
                            print("Worker proccess failed on:")
                            print(result)
                        raise Exception(e)
                    _stats = next(stats)
                    print(job_ids, _stats, finished, package_id, action, reason)
                    if error:
                        # NOTE: you can pipe stderr from the portal-update command to be able to tell if there are any errors
                        print(job_ids, _stats, finished, package_id, 'ERROR', error, file=sys.stderr)

                    append_log(finished, package_id, action, reason, error)
                    job_ids, finished, result = next(pool)

                    # save the sync state in the database
                    last_successful_sync = None
                    if do_update_sync_success_time:
                        last_successful_sync = datetime.now(timezone.utc)
                    else:
                        sync_obj = canada_model.PackageSync.get(package_id=package_id)
                        if sync_obj:
                            last_successful_sync = sync_obj.last_successful_sync

                    canada_model.PackageSync.upsert(package_id=package_id,
                                                    last_successful_sync=last_successful_sync,
                                                    error_on=failure_reason or None,
                                                    error=failure_trace or None)

                print(" --- next batch starting at: " + next_date.isoformat())
                append_log(
                    None,
                    None,
                    "next batch starting at:",
                    next_date.isoformat()
                )
                self._portal_update_activity_date = next_date.isoformat()
            self._portal_update_completed = True


def _changed_packages_since(registry: LocalCKAN, since_time: str,
                            ids_only: Optional[bool]=False, verbose: Optional[bool]=False):
    """
    PortalUpdater member: Gathers packages based on activity.

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
    if verbose:
        if ids_only:
            print("Only retrieving changed package IDs...", file=sys.stderr)
        else:
            print("Retrieving changed package dicts, resource views, and resource dictionaries...", file=sys.stderr)
    for result in data:
        package_id = result['package_id']
        try:
            source_package = registry.action.package_show(id=package_id)
        except NotFound:
            print(package_id + " not found in database.", file=sys.stderr)
        else:
            if ids_only:
                # ckanapi workers are expecting bytes
                packages.append(source_package['id'].encode('utf-8'))
            else:
                source_package = get_datastore_and_views(source_package, registry, verbose=verbose)
                # ckanapi workers are expecting bytes
                packages.append(json.dumps(source_package).encode('utf-8'))

    if data:
        since_time = isodate(data[-1]['timestamp'], None)

    return packages, since_time


def _copy_datasets(source_datastore_uri: Optional[Union[str, None]], user: Optional[Union[str, None]]=None,
                   mirror: Optional[bool]=False, verbose: Optional[bool]=False):
    """
    PortalUpdater member: Syncs package dicts from the stdin (valid JSON).

    A process that accepts packages on stdin which are compared o the local version of the same package.
    The local package is hen created, updated, deleted or left unchanged. This process outputs that
    action as a string 'created', 'updated', 'deleted' or 'unchanged'.
    """
    with _quiet_int_pipe():
        portal = LocalCKAN(username = user)

        now = datetime.now()

        packages = iter(sys.stdin.readline, '')
        for package in packages:

            failure_reason = ''
            failure_trace = ''
            error =  ''  # will output to stderr, while action gets outputted to stdout
            do_update_sync_success_time = False

            @contextmanager
            def _capture_exception_details(_reason: str, _package_id: str):
                """
                Context manager to handle exceptions for Package actions.
                """
                nonlocal failure_reason, failure_trace, error, do_update_sync_success_time
                try:
                    yield
                except Exception as e:
                    failure_reason = _reason
                    failure_trace = traceback.format_exc()
                    # do not need to concatenate as there can only be one error for packages
                    error = '\n  %s failed for ' % _reason
                    if _package_id:
                        error += '%s ' % _package_id
                    else:
                        error += 'unknown '
                    error += str(e)
                    if verbose:
                        error += '\n    Failed with Error: %s' % failure_trace
                    do_update_sync_success_time = False
                    pass

            source_pkg = json.loads(package)
            package_id = source_pkg['id']
            reason = ''
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

                target_pkg = get_datastore_and_views(target_pkg, portal, verbose=verbose)
                _trim_package(target_pkg)

            resource_file_hashes = {}

            if action == 'skip':
                pass
            elif target_pkg is None and source_pkg is None:
                action = 'unchanged'
                reason = reason or 'deleted on registry'
                do_update_sync_success_time = False  # do not update sync time if nothing changed
            elif target_deleted:
                action = 'updated'
                reason = 'undeleting on target'
                with _capture_exception_details('package_update', package_id):
                    portal.action.package_update(**source_pkg)
                    do_update_sync_success_time = True
                if not failure_reason:  # only try adding datastores and views if no errors
                    for r in source_pkg['resources']:
                        # use Registry file hashes for force undelete
                        resource_file_hashes[r['id']] = r.get('hash')
                    _action, _error, failure_reason, failure_trace = _add_datastore_and_views(source_pkg, portal,
                                                                                              resource_file_hashes,
                                                                                              source_datastore_uri,
                                                                                              verbose=verbose)
                    action += _action
                    error += _error
                    if failure_reason:
                        reason += ' ERRORED'
                        do_update_sync_success_time = False
                else:
                    reason += ' ERRORED'
                    do_update_sync_success_time = False
            elif target_pkg is None:
                action = 'created'
                with _capture_exception_details('package_create', package_id):
                    portal.action.package_create(**source_pkg)
                    do_update_sync_success_time = True
                if not failure_reason:  # only try adding datastores and views if no errors
                    _action, _error, failure_reason, failure_trace = _add_datastore_and_views(source_pkg, portal,
                                                                                              resource_file_hashes,
                                                                                              source_datastore_uri,
                                                                                              verbose=verbose)
                    action += _action
                    error += _error
                    if failure_reason:
                        reason += ' ERRORED'
                        do_update_sync_success_time = False
                else:
                    reason += ' ERRORED'
                    do_update_sync_success_time = False
            elif source_pkg is None:
                action = 'deleted'
                with _capture_exception_details('package_delete', package_id):
                    portal.action.package_delete(id=package_id)
                    do_update_sync_success_time = True
                if failure_reason:
                    reason += ' ERRORED'
                    do_update_sync_success_time = False
            elif source_pkg == target_pkg:
                action = 'unchanged'
                reason = 'no difference found'
                do_update_sync_success_time = False  # do not update sync time if nothing changed
            else:
                action = 'updated'
                for r in target_pkg['resources']:
                    # use Portal file hashes
                    resource_file_hashes[r['id']] = r.get('hash')
                with _capture_exception_details('package_update', package_id):
                    portal.action.package_update(**source_pkg)
                    do_update_sync_success_time = True
                if not failure_reason:  # only try adding datastores and views if no errors
                    _action, _error, failure_reason, failure_trace = _add_datastore_and_views(source_pkg, portal,
                                                                                              resource_file_hashes,
                                                                                              source_datastore_uri,
                                                                                              verbose=verbose)
                    error += _error
                    action += _action
                    if failure_reason:
                        reason += ' ERRORED'
                        do_update_sync_success_time = False
                else:
                    reason += ' ERRORED'
                    do_update_sync_success_time = False

            sys.stdout.write(json.dumps([package_id, action, reason, error, failure_reason, failure_trace, do_update_sync_success_time]) + '\n')
            sys.stdout.flush()


def _changed_datasets(since_date, server, brief):
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


def _resource_size_update(size_report):
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


def _resource_https_update(https_report, https_alt_report):
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


def _load_suggested(use_created_date, filename):
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


def _trim_package(pkg: Optional[Union[dict, None]]=None):
    """
    PortalUpdater member: removes keys from provided package dict.

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


def _add_datastore_and_views(package: dict, portal: LocalCKAN, resource_file_hashes: dict,
                             source_datastore_uri: str, verbose: Optional[bool]=False) -> Tuple[str, str, str, str]:
    """
    PortalUpdater member: Syncs DataDictionaries, Resource Views, and DataStore tables.
    """
    # create datastore table and views for each resource of the package
    action = ''
    error = ''
    failure_reason = ''
    failure_trace = ''
    for resource in package['resources']:
        res_id = resource['id']
        if res_id in package.keys():
            if 'data_dict' in package[res_id].keys():
                _action, _error, _failure_reason, _failure_trace = _add_to_datastore(portal, resource,
                                                                                     package[res_id], resource_file_hashes,
                                                                                     source_datastore_uri, verbose=verbose)
                action += _action
                error += _error
                if failure_reason:
                    failure_reason += ',%s' % _failure_reason  # comma separate multiple failure reasons
                    failure_trace += '\n\n%s' % _failure_trace  # separate multiple failure traces with newlines
                else:
                    failure_reason = _failure_reason
                    failure_trace = _failure_trace
            if 'views' in package[res_id].keys():
                _action, _error, _failure_reason, _failure_trace = _add_views(portal, resource, package[res_id], verbose=verbose)
                action += _action
                error += _error
                if failure_reason:
                    failure_reason += ',%s' % _failure_reason  # comma separate multiple failure reasons
                    failure_trace += '\n\n%s' % _failure_trace  # separate multiple failure traces with newlines
                else:
                    failure_reason = _failure_reason
                    failure_trace = _failure_trace
    return action, error, failure_reason, failure_trace


def _add_to_datastore(portal: LocalCKAN, resource: dict, resource_details: dict,
                      resource_file_hashes: dict, source_datastore_uri: str, verbose: Optional[bool]=False) -> Tuple[str, str, str, str]:
    """
    PortalUpdater member: Syncs DataDictionaries and DataStore tables.
    """
    action = ''
    error = ''
    failure_reason = ''
    failure_trace = ''

    @contextmanager
    def _capture_exception_details(_reason: str, _resource_id: str):
        """
        Context manager to handle exceptions for DataStore Resource actions.
        """
        nonlocal failure_reason, failure_trace, error
        try:
            yield
        except Exception as e:
            if failure_reason:
                # comma separate multiple failure reasons
                failure_reason += ',%s' % _reason
            else:
                failure_reason = _reason
            if _resource_id:
                failure_reason += "[resource_id=%s]" % _resource_id
            if failure_trace:
                # separate multiple failure traces with newlines
                failure_trace += '\n\n%s' % traceback.format_exc()
            else:
                failure_trace = traceback.format_exc()
            # always concatenate as there can be multiple errors
            error += '\n  %s failed for ' % _reason
            if _resource_id:
                error += 'resource %s ' % _resource_id
            else:
                error += 'unknown '
            error += str(e)
            if verbose:
                error += '\n    Failed with Error: %s' % failure_trace
            pass

    try:
        portal.call_action('datastore_search', {'resource_id': resource['id'], 'limit': 0})
        if resource_file_hashes.get(resource['id']) \
                and resource_file_hashes.get(resource['id']) == resource.get('hash')\
                and _datastore_dictionary(portal, resource['id']) == resource_details['data_dict']:
            if verbose:
                action += '\n  File hash and Data Dictionary has not changed, skipping DataStore for %s...' % resource['id']
            return action, error, failure_reason, failure_trace
        else:
            with _capture_exception_details('datastore_delete', resource['id']):
                portal.call_action('datastore_delete', {"id": resource['id'], "force": True})
                action += '\n  datastore-deleted for ' + resource['id']
    except NotFound:
        # not an issue, resource does not exist in datastore
        if verbose:
            action += '\n  DataStore does not exist for resource %s...trying to create it...' % resource['id']
        pass

    datastore_created = False
    with _capture_exception_details('datastore_create', resource['id']):
        portal.call_action('datastore_create',
                           {"resource_id": resource['id'],
                            "fields": resource_details['data_dict'],
                            "force": True})

        action += '\n  datastore-created for ' + resource['id']
        datastore_created = True

    if datastore_created:
        # load data only if datastore_create was successful
        target_datastore_uri = str(datastore.get_write_engine().url)
        cmd1 = subprocess.Popen(['pg_dump', source_datastore_uri, '-a', '-t', resource['id']], stdout=subprocess.PIPE)
        cmd2 = subprocess.Popen(['psql', target_datastore_uri], stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = cmd2.communicate()
        if not err:
            action += ' data-loaded'
            if verbose:
                if resource_details['data_dict']:
                    action += '\n    Using DataStore fields:'
                    for field in resource_details['data_dict']:
                        action += '\n      %s' % field['id']
                else:
                    action += '\n    There are no DataStore fields!!!'
        else:
            with _capture_exception_details('datastore_load', resource['id']):
                raise datastore.DataError('Failed to dump and load datastore data from the Registry to the Portal')
            # special addition of subprocess error output, we know that an error has occurred
            if failure_reason:
                failure_trace += '\n\npsql command error: %s' % err  # output pg_dump and psql load command errors
            else:
                failure_trace += '\n\npsql command error: %s' % err  # output pg_dump and psql load command errors

    return action, error, failure_reason, failure_trace


def _add_views(portal: LocalCKAN, resource: dict, resource_details: dict, verbose: Optional[bool]=False) -> Tuple[str, str, str, str]:
    """
    PortalUpdater member: Syncs Resource Views.
    """
    action = ''
    error = ''
    failure_reason = ''
    failure_trace = ''

    @contextmanager
    def _capture_exception_details(_reason: Union[str, None], _resource_id: str, _view_id: str):
        """
        Context manager to handle exceptions for Resource View actions.
        """
        nonlocal failure_reason, failure_trace, error
        try:
            yield
        except Exception as e:
            if failure_reason:
                # comma separate multiple failure reasons
                failure_reason += ',%s' % _reason
            else:
                failure_reason = _reason
            if _resource_id:
                failure_reason += "[resource_id=%s]" % _resource_id
            if _view_id:
                failure_reason += "[view_id=%s]" % _view_id
            if failure_trace:
                # separate multiple failure traces with newlines
                failure_trace += '\n\n%s' % traceback.format_exc()
            else:
                failure_trace = traceback.format_exc()
            # always concatenate as there can be multiple errors
            error += '\n  %s failed for ' % _reason
            if _resource_id and _view_id:
                error += 'view %s for resource %s ' % (_view_id, _resource_id)
            else:
                error += 'unknown '
            error += str(e)
            if verbose:
                error += '\n    Failed with Error: %s' % failure_trace
            pass

    target_views = portal.call_action('resource_view_list', {'id': resource['id']})
    for src_view in resource_details['views']:
        view_action = 'resource_view_create'
        for target_view in target_views:
            if target_view['id'] == src_view['id']:
                view_action = None if target_view == src_view else 'resource_view_update'

        if view_action:
            with _capture_exception_details(view_action, resource['id'], src_view['id']):
                portal.call_action(view_action, src_view)
                action += '\n  %s %s for resource %s' % (view_action, src_view['id'], resource['id'])

    for target_view in target_views:
        to_delete = True
        for src_view in resource_details['views']:
            if target_view['id'] == src_view['id']:
                to_delete = False
                break
        if to_delete:
            view_action = 'resource_view_delete'
            with _capture_exception_details(view_action, resource['id'], src_view['id']):
                portal.call_action(view_action, {'id':target_view['id']})
                action += '\n  %s %s for resource %s' % (view_action, src_view['id'], resource['id'])

    return action, error, failure_reason, failure_trace


def get_datastore_and_views(package, ckan_instance, verbose=False):
    if package and 'resources' in package:
        for resource in package['resources']:
            # check if resource exists in datastore
            if resource['datastore_active']:
                if verbose:
                    print("DataStore is active for %s" % resource['id'], file=sys.stderr)
                    print("  Getting resource views and DataStore fields...", file=sys.stderr)
                try:
                    table = ckan_instance.call_action('datastore_search',
                                                      {'resource_id': resource['id'],
                                                       'limit': 0})
                    if table:
                        # add hash, views and data dictionary
                        package[resource['id']] = {
                            "hash": resource.get('hash'),
                            "views": ckan_instance.call_action('resource_view_list',
                                                               {'id': resource['id']}),
                            "data_dict": _datastore_dictionary(ckan_instance, resource['id']),
                        }
                except NotFound:
                    if verbose:
                        print("  WARNING: Did not find resource views or DataStore fields...", file=sys.stderr)
                    pass
                except ValidationError as e:
                    raise ValidationError({
                        'original_error': repr(e),
                        'original_error_dict': e.error_dict,
                        'resource_id': resource['id'],
                    })
            else:
                if verbose:
                    print("DataStore is inactive for %s" % resource['id'], file=sys.stderr)
                    print("  Only getting resource views...", file=sys.stderr)
                resource_views = ckan_instance.call_action('resource_view_list',
                                                           {'id': resource['id']})
                if resource_views:
                    package[resource['id']] = {
                        "views": resource_views}
    return package


def _update_inventory_votes(json_name):
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


def _datastore_dictionary(ckan_instance, resource_id):
    """
    Return the data dictionary info for a resource
    """
    try:
        return [
            f for f in ckan_instance.call_action('datastore_search', {
                    u'resource_id': resource_id,
                    u'limit': 0,
                    u'include_total': False})['fields']
            if not f['id'].startswith(u'_')]
    except (NotFound, NotAuthorized):
        return []


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


def _get_user(user:Optional[Union[str, None]]=None) -> str:
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Increase verbosity",
)
def portal_update(portal_ini,
                  ckan_user,
                  last_activity_date=None,
                  processes=1,
                  mirror=False,
                  log=None,
                  tries=1,
                  delay=60,
                  verbose=False):
    """
    PortalUpdater member: CKAN cli command entrance to run the PortalUpdater stack.

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
    PortalUpdater(portal_ini,
                  ckan_user,
                  last_activity_date,
                  processes,
                  mirror,
                  log,
                  tries,
                  delay,
                  verbose).portal_update()


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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Increase verbosity",
)
def copy_datasets(mirror: Optional[bool]=False, ckan_user: Optional[Union[str, None]]=None,
                  source: Optional[Union[str, None]]=None, verbose: Optional[bool]=False):
    """
    PortalUpdater member: CKAN cli command entrance to sync packages from stdin (valid JSON).

    A process that accepts packages on stdin which are compared to the local version of the same package.
    The local package is then created, updated, deleted or left unchanged. This process outputs that
    action as a string 'created', 'updated', 'deleted' or 'unchanged'.

    Full Usage:\n
        canada copy-datasets [-m] [-o <source url>]
    """
    _copy_datasets(source,
                   _get_user(ckan_user),
                   mirror,
                   verbose)



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
    _changed_datasets(since_date,
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
    _load_suggested(use_created_date,
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
    _update_inventory_votes(votes_json)


@canada.command(short_help="Tries to update resource sizes from a CSV file.")
@click.argument("resource_sizes_csv")
def resource_size_update(resource_sizes_csv):
    """
    Tries to update resource sizes from a CSV file.

    Full Usage:\n
        canada resource-size-update <resource_sizes.csv>
    """
    _resource_size_update(resource_sizes_csv)


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
    info = get_action('datastore_search')(context, {"resource_id": resource_id, "limit": 0})
    return info.get('total')


def _error_message(message):
    click.echo("\n\033[1;33m%s\033[0;0m\n\n" % message)


def _success_message(message):
    click.echo("\n\033[0;36m\033[1m%s\033[0;0m\n\n" % message)


@canada.command(short_help="Sets datastore_active to False for Invalid Resources.")
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
        resource_ids = _get_datastore_resources(valid=False, verbose=verbose)  # gets invalid Resources, w/ datastore_active=1
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


@canada.command(short_help="Re-submits valid DataStore Resources to Validation OR Xloader.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to re-submit to Validation. Defaults to None.')
@click.option('-e', '--empty-only', is_flag=True, type=click.BOOL, help='Only re-submit empty DataStore Resources.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of submitting them to Validation.')
@click.option('-x', '--xloader', is_flag=True, type=click.BOOL,
              help='Submits the resources to Xloader instead of Validation. Will Xloader even if file hash has not changed.')
@click.option('-f', '--failed', is_flag=True, type=click.BOOL,
              help='Only re-submit resources that failed. Mutually exclusive with --empty-only.')
def resubmit_datastore_resources(resource_id=None, empty_only=False, verbose=False, quiet=False, list=False, xloader=False, failed=False):
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
        resource_ids = _get_datastore_resources(verbose=verbose)  # gets valid Resources, w/ datastore_active=1
        max = len(resource_ids)
        for resource_id in resource_ids:
            if resource_id in resource_ids_to_submit:
                continue
            if resource_id in datastore_tables:
                try:
                    if empty_only:
                        count = _get_datastore_count(context, resource_id, verbose=verbose, status=status, max=max)
                        if int(count) == 0:
                            if verbose:
                                click.echo("%s/%s -- Resource %s has %s rows in DataStore. Let's fix this one..." % (status, max, resource_id, count))
                            resource_ids_to_submit.append(resource_id)
                        elif verbose:
                            click.echo("%s/%s -- Resource %s has %s rows in DataStore. Skipping..." % (status, max, resource_id, count))
                    elif failed:
                        if xloader:
                            # check xloader status
                            try:
                                xloader_job = get_action('xloader_status')({'ignore_auth': True},
                                                                           {'resource_id': resource_id})
                            except Exception as e:
                                if verbose:
                                    errors.write('Failed to get XLoader Report for Resource %s with errors:\n\n%s' % (resource_id, e))
                                    errors.write('\n')
                                    traceback.print_exc(file=errors)
                                xloader_job = {}
                                pass
                            if xloader_job.get('status') == 'error':
                                resource_ids_to_submit.append(resource_id)
                                if verbose:
                                    click.echo("%s/%s -- Going to re-submit Resource %s..." % (status, max, resource_id))
                            elif verbose:
                                click.echo("%s/%s -- Resource %s did not fail XLoader. Skipping..." % (status, max, resource_id))
                        else:
                            # check validation status
                            try:
                                res_dict = get_action('resource_show')({'ignore_auth': True},
                                                                       {'id': resource_id})
                            except Exception as e:
                                if verbose:
                                    errors.write('Failed to get Resource %s with errors:\n\n%s' % (resource_id, e))
                                    errors.write('\n')
                                    traceback.print_exc(file=errors)
                                res_dict = {}
                                pass
                            if res_dict.get('validation_status') == 'failure':
                                resource_ids_to_submit.append(resource_id)
                                if verbose:
                                    click.echo("%s/%s -- Going to re-submit Resource %s..." % (status, max, resource_id))
                            elif verbose:
                                click.echo("%s/%s -- Resource %s did not fail Validation. Skipping..." % (status, max, resource_id))
                    else:
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("%s/%s -- Going to re-submit Resource %s..." % (status, max, resource_id))
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
            if empty_only:
                count = _get_datastore_count(context, resource_id, verbose=verbose)
                if int(count) == 0:
                    if verbose:
                        click.echo("1/1 -- Resource %s has %s rows in DataStore. Let's fix this one..." % (resource_id, count))
                    resource_ids_to_submit.append(resource_id)
                elif verbose:
                    click.echo("1/1 -- Resource %s has %s rows in DataStore. Skipping..." % (resource_id, count))
            elif failed:
                if xloader:
                    # check xloader status
                    try:
                        xloader_job = get_action('xloader_status')({'ignore_auth': True},
                                                                   {'resource_id': resource_id})
                    except Exception as e:
                        if verbose:
                            errors.write('Failed to get XLoader Report for Resource %s with errors:\n\n%s' % (resource_id, e))
                            errors.write('\n')
                            traceback.print_exc(file=errors)
                        xloader_job = {}
                        pass
                    if xloader_job.get('status') == 'error':
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("1/1 -- Going to re-submit Resource %s..." % (resource_id))
                    elif verbose:
                        click.echo("1/1 -- Resource %s did not fail XLoader. Skipping..." % (resource_id))
                else:
                    # check validation status
                    try:
                        res_dict = get_action('resource_show')({'ignore_auth': True},
                                                               {'id': resource_id})
                    except Exception as e:
                        if verbose:
                            errors.write('Failed to get Resource %s with errors:\n\n%s' % (resource_id, e))
                            errors.write('\n')
                            traceback.print_exc(file=errors)
                        res_dict = {}
                        pass
                    if res_dict.get('validation_status') == 'failure':
                        resource_ids_to_submit.append(resource_id)
                        if verbose:
                            click.echo("1/1 -- Going to re-submit Resource %s..." % (resource_id))
                    elif verbose:
                        click.echo("1/1 -- Resource %s did not fail Validation. Skipping..." % (resource_id))
            else:
                resource_ids_to_submit.append(resource_id)
                if verbose:
                    click.echo("1/1 -- Going to re-submit Resource %s..." % (resource_id))
        except Exception as e:
            if verbose:
                errors.write('Failed to get DataStore info for Resource %s with errors:\n\n%s' % (resource_id, e))
                errors.write('\n')
                traceback.print_exc(file=errors)
            pass

    if resource_ids_to_submit and not quiet and not list:
        if xloader:
            click.confirm("Do you want to re-submit %s Resources to Xloader?" % len(resource_ids_to_submit), abort=True)
        else:
            click.confirm("Do you want to re-submit %s Resources to Validation?" % len(resource_ids_to_submit), abort=True)

    status = 1
    max = len(resource_ids_to_submit)
    for id in resource_ids_to_submit:
        if list:
            click.echo(id)
        else:
            try:
                if xloader:
                    get_action('xloader_submit')(context, {"resource_id": id, "ignore_hash": True})
                    msg = "%s/%s -- Submitted Resource %s to Xloader" % (status, max, id)
                else:
                    get_action('resource_validation_run')(context, {"resource_id": id, "async": True})
                    msg = "%s/%s -- Submitted Resource %s to Validation" % (status, max, id)
                if verbose:
                    click.echo(msg)
            except Exception as e:
                if verbose:
                    if xloader:
                        errors.write('Failed to submit Resource %s to Xloader with errors:\n\n%s' % (id, e))
                    else:
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
        if xloader:
            _success_message('Re-submitted %s Resources to Xloader.' % len(resource_ids_to_submit))
        else:
            _success_message('Re-submitted %s Resources to Validation.' % len(resource_ids_to_submit))
    elif not resource_ids_to_submit:
        _success_message('No valid, empty DataStore Resources to re-submit at this time.')


@canada.command(short_help="Deletes Invalid Resource DataStore tables.")
@click.option('-r', '--resource-id', required=False, type=click.STRING, default=None,
              help='Resource ID to delete the DataStore table for. Defaults to None.')
@click.option('-d', '--delete-table-views', is_flag=True, type=click.BOOL, help='Deletes any Datatable Views from the Resource.')
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-q', '--quiet', is_flag=True, type=click.BOOL, help='Suppress human interaction.')
@click.option('-l', '--list', is_flag=True, type=click.BOOL, help='List the Resource IDs instead of deleting their DataStore tables.')
@click.option('-e', '--any-empty', is_flag=True, type=click.BOOL, help='Deletes any empty DataStore tables, valid or invalid Resources.')
def delete_invalid_datastore_tables(resource_id=None, delete_table_views=False, verbose=False, quiet=False, list=False, any_empty=False):
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
        resource_ids = _get_datastore_resources(valid=get_valid, verbose=verbose)  # w/ datastore_active=1
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


@canada.command(short_help="Deletes all datatable views from non-datastore Resources.")
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
        resource_ids = _get_datastore_resources(valid=None, is_datastore_active=False, verbose=verbose)  # gets invalid and valid Resources, w/ datastore_active=1|0
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


@canada.command(short_help="Generates the report for dataset Opennes Ratings.")
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
@click.option('-d', '--details', is_flag=True, type=click.BOOL, help='Include more dataset details.')
@click.option('-D', '--dump', type=click.File('w'), help='Dump results to a CSV file.')
@click.option('-p', '--package-id', type=click.STRING, default='c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7',
              help='Dataset ID, defaults to c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7')
def openness_report(verbose=False, details=False, dump=False, package_id='c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7'):
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

    def iter_records():
        _records = []
        try:
            with gzip.GzipFile(fileobj=zf, mode='rb') as fd:
                for line in fd:
                    _records.append(json.loads(line.decode('utf-8')))
                    if len(_records) >= 50:
                        yield (_records)
                        _records = []
            if len(_records) >0:
                yield (_records)
        except GeneratorExit:
            pass
        except:
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
                title = title.get('en', title.get('en-t-fr', '')) + ' | ' + title.get('fr', title.get('fr-t-en', ''))
                url = ''.join(['https://open.canada.ca/data/en/dataset/', id, ' | ',
                      'https://ouvert.canada.ca/data/fr/dataset/', id])
                report.append([title, url, score])

        if verbose:
            click.echo("Dumping detailed openness ratings to %s" % getattr(dump, 'name', 'stdout'))

        orgs = list(reports)
        orgs.sort()
        if dump:
            outf = dump
        else:
            outf = sys.stdout
        outf.write(BOM)
        out = csv.writer(outf)
        #Header
        out.writerow(["Department Name Englist | Nom du ministère en français",
                      "Title English | Titre en français",
                      "URL",
                      "Openness Rating | Cote d'ouverture",])
        for k in orgs:
            rlist = reports[k]
            for r in rlist:
                line=[k, r[0], r[1], r[2]]
                out.writerow(line)
        if dump:
            outf.close()
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
    outf.write(BOM)
    out = csv.writer(outf)
    #Header
    out.writerow(["Department Name English / Nom du ministère en anglais",
                    "Department Name French / Nom du ministère en français",
                    "Openness report (score:count) / Rapport d'ouverture (score: compter)",])
    for k,v in reports.items():
        names = list(map(lambda x: x.strip(), k.split('|')))
        line=[names[0], names[1], dict(v)]
        out.writerow(line)
    if dump:
        outf.close()
    if verbose:
        click.echo("Done!")


@canada.command(short_help="Deletes old database triggers.")
@click.option('-v', '--verbose', is_flag=True, type=click.BOOL, help='Increase verbosity.')
def delete_old_triggers(verbose=False):
    """
    Delete old, unused database triggers.
    """
    _drop_function('no_surrounding_whitespace_error', verbose)
    _drop_function('year_optional_month_day_error', verbose)
    _drop_function('choices_from', verbose)
    _drop_function('integer_or_na_nd_error', verbose)
    _drop_function('inventory_trigger', verbose)


def _drop_function(name, verbose=False):
    sql = u'''
        DROP FUNCTION {name};
        '''.format(name=datastore.identifier(name))

    try:
        datastore._write_engine_execute(sql)
    except datastore.ProgrammingError as pe:
        if verbose:
            click.echo('Failed to drop function: {0}\n{1}'.format(
                name, str(datastore._programming_error_summary(pe))), err=True)
        pass
