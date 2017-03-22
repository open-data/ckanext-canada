#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ckan.lib.cli import CkanCommand
from ckan.logic.validators import isodate, boolean_validator
from ckan.lib.navl.dictization_functions import Invalid
import paste.script
from paste.script.util.logging_config import fileConfig
from ckanapi.cli.workers import worker_pool
from ckanapi.cli.utils import completion_stats
import ckan.lib.uploader as uploader

import re
import os
import json
import time
import sys
import urllib2
from datetime import datetime, timedelta
from contextlib import contextmanager

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.metadata_xform import metadata_xform

from ckantoolkit import h

from ckanapi import (
    RemoteCKAN,
    LocalCKAN,
    NotFound,
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

DATASET_TYPES = 'info', 'dataset'


class CanadaCommand(CkanCommand):
    """
    CKAN Canada Extension

    Usage::

        paster canada portal-update <remote server>
                                    [<last activity date> | [<k>d][<k>h][<k>m]]
                                    [-f | -a <push-apikey>] [-p <num>] [-m]
                                    [-l <log file>] [-t <num> [-d <seconds>]]
                      copy-datasets <remote server> [<dataset-id> ...]
                                    [-f | -a <push-apikey>] [-m]
                      changed-datasets [<since date>] [-s <remote server>] [-b]
                      metadata-xform [--portal]
                      update-triggers

        <last activity date> for reading activites, default: 7 days ago
        <k> number of hours/minutes/seconds in the past for reading activities

    Options::

        -a/--push-apikey <apikey>   push to <remote server> using apikey
        -b/--brief                  don't output requested dates
        -c/--config <ckan config>   use named ckan config file
                                    (available to all commands)
        -d/--delay <seconds>        delay between retries, default: 60
        -f/--fetch                  fetch datasets from <remote server>,
                                    must be specified if push apikey not
                                    given
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
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option(
        '-c',
        '--config',
        dest='config',
        default='development.ini',
        help='Config file to use.'
    )
    parser.add_option(
        '-p',
        '--processes',
        dest='processes',
        default=1,
        type='int'
    )
    parser.add_option(
        '-u',
        '--ckan-user',
        dest='ckan_user',
        default=None
    )
    parser.add_option('-l', '--log', dest='log', default=None)
    parser.add_option('-m', '--mirror', dest='mirror', action='store_true')
    parser.add_option(
        '-a',
        '--push-apikey',
        dest='push_apikey',
        default=None
    )
    parser.add_option('-s', '--server', dest='server', default=None)
    parser.add_option('-b', '--brief', dest='brief', action='store_true')
    parser.add_option('-f', '--fetch', dest='fetch', action='store_true')
    parser.add_option('-t', '--tries', dest='tries', default=1, type='int')
    parser.add_option('-d', '--delay', dest='delay', default=60, type='float')
    parser.add_option('--portal', dest='portal', action='store_true')

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'portal-update':
            self.portal_update(self.args[1], *self.args[2:])

        elif cmd == 'copy-datasets':
            with _quiet_int_pipe():
                self.copy_datasets(self.args[1], self.args[2:])

        elif cmd == 'changed-datasets':
            self.changed_datasets(*self.args[1:])

        elif cmd == 'metadata-xform':
            metadata_xform(self.options.portal)

        elif cmd == 'update-triggers':
            self.update_triggers()

        else:
            print self.__doc__

    def _app_config(self):
        """
        This is the first part of CkanCommand._load_config()
        """
        from paste.deploy import appconfig
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        if not os.path.exists(self.filename):
            raise AssertionError(
                'Config filename %r does not exist.' % self.filename
            )
        fileConfig(self.filename)
        appconfig('config:' + self.filename)

    def portal_update(self, source, activity_date=None):
        """
        collect batches of package ids modified at source since activity_date
        and apply the package updates to the local CKAN instance for all
        packages with published_date set to any time in the past.
        """
        tries = self.options.tries
        self._portal_update_completed = False
        self._portal_update_activity_date = activity_date
        while tries > 0:
            tries -= 1
            self._portal_update(source, self._portal_update_activity_date)
            if self._portal_update_completed or not tries:
                return
            time.sleep(self.options.delay)

    def _portal_update(self, source, activity_date):
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
        if self.options.log:
            log = open(self.options.log, 'a')

        if self.options.push_apikey and not self.options.fetch:
            registry = LocalCKAN()
        elif self.options.fetch:
            registry = RemoteCKAN(source)
        else:
            print "exactly one of -f or -a options must be specified"
            return

        def changed_package_id_runs(start_date):
            while True:
                package_ids, next_date = self._changed_package_ids_since(
                    registry, start_date)
                if next_date is None:
                    return
                yield package_ids, next_date
                start_date = next_date

        cmd = [
            sys.argv[0],
            'canada',
            'copy-datasets',
            source,
            '-c',
            self.options.config
        ]
        if self.options.push_apikey:
            cmd.extend(['-a', self.options.push_apikey])
        else:
            cmd.append('-f')
        if self.options.mirror:
            cmd.append('-m')

        pool = worker_pool(
            cmd,
            self.options.processes,
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

            for package_ids, next_date in (
                    changed_package_id_runs(activity_date)):
                job_ids, finished, result = pool.send(enumerate(package_ids))
                stats = completion_stats(self.options.processes)
                while result is not None:
                    package_id, action, reason = json.loads(result)
                    print job_ids, stats.next(), finished, package_id, \
                        action, reason
                    append_log(finished, package_id, action, reason)
                    job_ids, finished, result = pool.next()

                print " --- next batch starting at: " + next_date.isoformat()
                append_log(
                    None,
                    None,
                    "next batch starting at:",
                    next_date.isoformat()
                )
                self._portal_update_activity_date = next_date.isoformat()
            self._portal_update_completed = True

    def _changed_package_ids_since(self, registry, since_time,
                                   seen_id_set=None):
        """
        Query source ckan instance for packages changed since_time.
        returns (package ids, next since_time to query) or (None, None)
        when no more changes are found.

        registry - LocalCKAN or RemoteCKAN instance
        since_time - local datetime to start looking for changes
        seen_id_set - set of package ids already processed, this set is
                      modified by calling this function

        If all the package ids found were included in seen_id_set this
        function will return an empty list of package ids.  Note that
        this is different than when no more changes found and (None, None)
        is returned.
        """
        data = registry.action.changed_packages_activity_list_since(
            since_time=since_time.isoformat())

        if seen_id_set is None:
            seen_id_set = set()

        if not data:
            return None, None

        package_ids = []
        for result in data:
            package_id = result['data']['package']['id']
            if package_id in seen_id_set:
                continue
            seen_id_set.add(package_id)
            package_ids.append(package_id)

        if data:
            since_time = isodate(data[-1]['timestamp'], None)

        return package_ids, since_time

    def copy_datasets(self, remote, package_ids=None):
        """
        a process that accepts package ids on stdin which are passed to
        the package_show API on the remote CKAN instance and compared
        to the local version of the same package.  The local package is
        then created, updated, deleted or left unchanged.  This process
        outputs that action as a string 'created', 'updated', 'deleted'
        or 'unchanged'
        """
        if self.options.push_apikey and not self.options.fetch:
            registry = LocalCKAN()
            portal = RemoteCKAN(remote, apikey=self.options.push_apikey)
        elif self.options.fetch:
            registry = RemoteCKAN(remote)
            portal = LocalCKAN()
        else:
            print "exactly one of -f or -a options must be specified"
            return

        now = datetime.now()

        if not package_ids:
            package_ids = iter(sys.stdin.readline, '')

        for package_id in package_ids:
            package_id = package_id.strip()
            reason = None
            target_deleted = False
            try:
                source_pkg = registry.action.package_show(id=package_id)
            except NotAuthorized:
                source_pkg = None
            except (CKANAPIError, urllib2.URLError), e:
                sys.stdout.write(
                    json.dumps([
                        package_id,
                        'source error',
                        unicode(e.args)
                    ]) + '\n'
                )
                raise
            if source_pkg and source_pkg['state'] == 'deleted':
                source_pkg = None

            if source_pkg and source_pkg['type'] not in DATASET_TYPES:
                # non-default dataset types ignored
                source_pkg = None

            _trim_package(source_pkg)

            if source_pkg and not self.options.mirror:
                # treat unpublished packages same as deleted packages
                if not source_pkg['portal_release_date']:
                    source_pkg = None
                    reason = 'release date not set'
                elif isodate(source_pkg['portal_release_date'], None) > now:
                    source_pkg = None
                    reason = 'release date in future'

            try:
                target_pkg = portal.call_action('package_show', {
                    'id': package_id
                })
            except (NotFound, NotAuthorized):
                target_pkg = None
            except (CKANAPIError, urllib2.URLError), e:
                sys.stdout.write(
                    json.dumps([
                        package_id,
                        'target error',
                        unicode(e.args)
                    ]) + '\n'
                )
                raise
            if target_pkg and target_pkg['state'] == 'deleted':
                target_pkg = None
                target_deleted = True

            _trim_package(target_pkg)

            if target_pkg is None and source_pkg is None:
                action = 'unchanged'
                reason = reason or 'deleted on registry'
            elif target_deleted:
                action = 'updated'
                reason = 'undeleting on target'
                portal.action.package_update(**source_pkg)
            elif target_pkg is None:
                action = 'created'
                portal.action.package_create(**source_pkg)
            elif source_pkg is None:
                action = 'deleted'
                portal.action.package_delete(id=package_id)
            elif source_pkg == target_pkg:
                action = 'unchanged'
                reason = 'no difference found'
            else:
                action = 'updated'
                portal.action.package_update(**source_pkg)

            sys.stdout.write(json.dumps([package_id, action, reason]) + '\n')
            sys.stdout.flush()

    def changed_datasets(self, since_date):
        """
        Produce a list of dataset ids and requested dates. Each package
        id will appear at most once, showing the activity date closest
        to since_date. Requested dates are preceeded with a "#"
        """
        since_date = isodate(since_date, None)
        seen_ids = set()

        if self.options.server:
            registry = RemoteCKAN(self.options.server)
        else:
            registry = LocalCKAN()

        while True:
            ids, since_date = self._changed_package_ids_since(
                registry, since_date, seen_ids)
            if not ids:
                return
            for i in ids:
                print i
            if not self.options.brief:
                print "# {0}".format(since_date.isoformat())


    def update_triggers(self):
        """Create/update triggers used by PD tables"""
        lc = LocalCKAN()
        choices = dict(
            (f['datastore_id'], f['choices'])
            for f in h.recombinant_choice_fields('consultations'))
        lc.action.datastore_function_create(
            name=u'consultations_trigger',
            or_replace=True,
            rettype=u'trigger',
            definition=u'''
                DECLARE
                    bad_partner_departments text := array_to_string(ARRAY(
                        SELECT unnest(NEW.partner_departments)
                        EXCEPT SELECT unnest({partner_departments})), ', ');
                    bad_subjects text := array_to_string(ARRAY(
                        SELECT unnest(NEW.subjects)
                        EXCEPT SELECT unnest({subjects})), ', ');
                    bad_goals text := array_to_string(ARRAY(
                        SELECT unnest(NEW.goals)
                        EXCEPT SELECT unnest({goals})), ', ');
                    bad_target_participants_and_audience text := array_to_string(ARRAY(
                        SELECT unnest(NEW.target_participants_and_audience)
                        EXCEPT SELECT unnest({target_participants_and_audience})), ', ');
                    bad_rationale text := array_to_string(ARRAY(
                        SELECT unnest(NEW.rationale)
                        EXCEPT SELECT unnest({rationale})), ', ');
                BEGIN
                    IF (NEW.registration_number = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: registration_number';
                    END IF;

                    IF NEW.publishable IS NULL THEN
                        RAISE EXCEPTION 'This field must not be empty: publishable';
                    END IF;

                    IF bad_partner_departments <> '' THEN
                        RAISE EXCEPTION 'Invalid choice for partner_departments: "%"', bad_partner_departments;
                    END IF;
                    NEW.partner_departments := ARRAY(
                        SELECT c FROM(SELECT unnest({partner_departments}) as c) u
                        WHERE c in (SELECT unnest(NEW.partner_departments)));

                    IF NOT (NEW.sector = ANY {sectors}) THEN
                        RAISE EXCEPTION 'Invalid choice for sector: "%"', NEW.sector;
                    END IF;

                    IF NEW.subjects = '{{}}' THEN
                        RAISE EXCEPTION 'This field must not be empty: subjects';
                    END IF;
                    IF bad_subjects <> '' THEN
                        RAISE EXCEPTION 'Invalid choice for subjects: "%"', bad_subjects;
                    END IF;
                    NEW.subjects := ARRAY(
                        SELECT c FROM(SELECT unnest({subjects}) as c) u
                        WHERE c in (SELECT unnest(NEW.subjects)));

                    IF (NEW.title_en = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: title_en';
                    END IF;

                    IF (NEW.title_fr = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: title_fr';
                    END IF;

                    IF NEW.goals = '{{}}' THEN
                        RAISE EXCEPTION 'This field must not be empty: goals';
                    END IF;
                    IF bad_goals <> '' THEN
                        RAISE EXCEPTION 'Invalid choice for goals: "%"', bad_goals;
                    END IF;
                    NEW.goals := ARRAY(
                        SELECT c FROM(SELECT unnest({goals}) as c) u
                        WHERE c in (SELECT unnest(NEW.goals)));

                    IF (NEW.description_en = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: description_en';
                    END IF;

                    IF (NEW.description_fr = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: description_fr';
                    END IF;

                    IF NOT (NEW.public_opinion_research = ANY {public_opinion_research}) THEN
                        RAISE EXCEPTION 'Invalid choice for public_opinion_research: "%"', NEW.public_opinion_research;
                    END IF;

                    IF NOT (NEW.public_opinion_research_standing_offer = ANY {public_opinion_research_standing_offer}) THEN
                        RAISE EXCEPTION 'Invalid choice for public_opinion_research_standing_offer: "%"', NEW.public_opinion_research_standing_offer;
                    END IF;

                    IF NEW.target_participants_and_audience = '{{}}' THEN
                        RAISE EXCEPTION 'This field must not be empty: target_participants_and_audience';
                    END IF;
                    IF bad_target_participants_and_audience <> '' THEN
                        RAISE EXCEPTION 'Invalid choice for target_participants_and_audience: "%"', bad_target_participants_and_audience;
                    END IF;
                    NEW.target_participants_and_audience := ARRAY(
                        SELECT c FROM(SELECT unnest({target_participants_and_audience}) as c) u
                        WHERE c in (SELECT unnest(NEW.target_participants_and_audience)));

                    IF NEW.planned_start_date IS NULL THEN
                        RAISE EXCEPTION 'This field must not be empty: planned_start_date';
                    END IF;

                    IF NEW.planned_end_date IS NULL THEN
                        RAISE EXCEPTION 'This field must not be empty: planned_end_date';
                    END IF;

                    IF NOT (NEW.status = ANY {status}) THEN
                        RAISE EXCEPTION 'Invalid choice for status: "%"', NEW.status;
                    END IF;

                    IF (NEW.further_information_en = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: further_information_en';
                    END IF;

                    IF (NEW.further_information_fr = '') IS NOT FALSE THEN
                        RAISE EXCEPTION 'This field must not be empty: further_information_fr';
                    END IF;

                    IF NEW.report_available_online IS NULL THEN
                        RAISE EXCEPTION 'This field must not be empty: report_available_online';
                    END IF;

                    IF NEW.rationale = '{{}}' THEN
                        RAISE EXCEPTION 'This field must not be empty: rationale';
                    END IF;
                    IF bad_rationale <> '' THEN
                        RAISE EXCEPTION 'Invalid choice for rationale: "%"', bad_rationale;
                    END IF;
                    NEW.rationale := ARRAY(
                        SELECT c FROM(SELECT unnest({rationale}) as c) u
                        WHERE c in (SELECT unnest(NEW.rationale)));

                    RETURN NEW;
                END;
                '''.format(
                    sectors=pg_array(choices['sector']),
                    partner_departments=pg_array(
                        choices['partner_departments']),
                    subjects=pg_array(choices['subjects']),
                    goals=pg_array(choices['goals']),
                    target_participants_and_audience=pg_array(
                        choices['target_participants_and_audience']),
                    public_opinion_research=pg_array(
                        choices['public_opinion_research']),
                    public_opinion_research_standing_offer=pg_array(
                        choices['public_opinion_research_standing_offer']),
                    status=pg_array(choices['status']),
                    rationale=pg_array(choices['rationale']),
                )
            )


def pg_array(choices):
    from ckanext.datastore.helpers import literal_string
    return u'(ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u'])'


def _trim_package(pkg):
    """
    remove keys from pkg that we don't care about when comparing
    or updating/creating packages.  Also try to convert types and
    create missing fields that will be present in package_show.
    """
    # XXX full of custom hacks and deep knowledge of our schema :-(
    if not pkg:
        return
    for k in ['extras', 'metadata_modified', 'metadata_created',
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
            'creator_user_id',
            ]:
        if k in pkg:
            del pkg[k]
    for r in pkg['resources']:
        for k in ['package_id', 'revision_id',
                'revision_timestamp', 'cache_last_updated',
                'webstore_last_updated', 'state', 'hash',
                'description', 'tracking_summary', 'mimetype_inner',
                'mimetype', 'cache_url', 'created', 'webstore_url',
                'last_modified', 'position']:
            if k in r:
                del r[k]
        for k in ['name', 'size']:
            if k not in r:
                r[k] = None
    for k in ['private']:
        pkg[k] = boolean_validator(unicode(pkg.get(k, '')), None)
    if 'name' not in pkg:
        pkg['name'] = pkg['id']
    if 'type' not in pkg:
        pkg['type'] = 'dataset'
    if 'state' not in pkg:
        pkg['state'] = 'active'
    for k in ['url']:
        if k not in pkg:
            pkg[k] = ''
    for name, lang, field in schema_description.dataset_field_iter():
        if field['type'] == 'date':
            try:
                pkg[name] = str(isodate(pkg[name], None)) if pkg.get(name) else ''
            except Invalid:
                pass # not for us to fail validation
        elif field['type'] == 'url':
            if not pkg.get(name): # be consistent about what an empty url is
                pkg[name] = ""
        elif field['type'] == 'fixed' and name in pkg:
            del pkg[name]


@contextmanager
def _quiet_int_pipe():
    """
    let pipe errors and KeyboardIterrupt exceptions cause silent exit
    """
    try:
        yield
    except KeyboardInterrupt:
        pass
    except IOError, e:
        if e.errno != 32:
            raise
