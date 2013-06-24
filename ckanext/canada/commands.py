from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic.validators import isodate, boolean_validator
from ckan.lib.navl.dictization_functions import Invalid
import paste.script
from paste.script.util.logging_config import fileConfig

import os
import json
import time
import sys
import gzip
from datetime import datetime, timedelta
from contextlib import contextmanager

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.workers import worker_pool
from ckanext.canada.stats import completion_stats
from ckanext.canada.navl_schema import convert_pilot_uuid_list
from ckanapi import (RemoteCKAN, LocalCKAN, NotFound,
    ValidationError, NotAuthorized, SearchIndexError)

class CanadaCommand(CkanCommand):
    """
    CKAN Canada Extension

    Usage::

        paster canada create-vocabularies
                      delete-vocabularies
                      create-organizations
                      load-datasets <.jl source file>
                                    [<starting line number> [<lines to load>]]
                                    [-r] [-p <num>] [-u <username>]
                                    [-l <log file>] [-z]
                      portal-update <remote server> [<last activity date>]
                                    [-p <num>] [-a <push-apikey>]
                      dump-datasets [-p <num>] [-z]

        <starting line number> of .jl source file, default: 1
        <lines to load> from .jl source file, default: all lines
        <last activity date> for reading activites, default: 7 days ago

    Options::

        -c/--config <ckan config>  use named ckan config file
                                   (available to all commands)
        -r/--replace-datasets      enable replacing existing datasets
        -p/--processes <num>       sets the number of worker processes,
                                   default: 1
        -u/--ckan-user <username>  sets the owner of packages created,
                                   default: ckan system user
        -l/--log <log filename>    write log of actions to log filename
        -a/--push-apikey <apikey>  push to <remote server> instead of
                                   pulling and use provided apikey
        -z/--gzip                  read/write gzipped data
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-r', '--replace-datasets', action='store_true',
        dest='replace_datasets', help='Replace existing datasets')
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
    parser.add_option('-p', '--processes', dest='processes',
        default=1, type="int")
    parser.add_option('-u', '--ckan-user', dest='ckan_user',
        default=None)
    parser.add_option('-l', '--log', dest='log', default=None)
    parser.add_option('-m', '--mirror', dest='mirror', action='store_true')
    parser.add_option('-a', '--push-apikey', dest='push_apikey',
        default=None)
    parser.add_option('-z', '--gzip', dest='gzip', action='store_true')

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'delete-vocabularies':
            for name in schema_description.vocabularies:
                self.delete_vocabulary(name)

        elif cmd == 'create-vocabularies':
            for name, terms in schema_description.vocabularies.iteritems():
                self.create_vocabulary(name, terms)

        elif cmd == 'create-organizations':
            for org in schema_description.dataset_field_by_id['owner_org']['choices']:
                if 'id' not in org:
                    continue
                if not org['id']:
                    print "skipping", org['key'].encode('utf-8')
                else:
                    self.create_organization(org)

        elif cmd == 'delete-organizations':
            raise NotImplementedError(
                "Sorry, this can't be implemented properly until group "
                "purging is implemented in CKAN")
            for org in schema_description.dataset_field_by_id['owner_org']['choices']:
                if 'id' not in org:
                    continue
                self.delete_organization(org)

        elif cmd == 'load-datasets':
            self.load_datasets(self.args[1], *self.args[2:])

        elif cmd == 'load-dataset-worker':
            with _quiet_int_pipe():
                self.load_dataset_worker()

        elif cmd == 'portal-update':
            self.portal_update(self.args[1], *self.args[2:])

        elif cmd == 'portal-update-worker':
            with _quiet_int_pipe():
                self.portal_update_worker(self.args[1])

        elif cmd == 'dump-datasets':
            self.dump_datasets()

        elif cmd == 'dump-datasets-worker':
            with _quiet_int_pipe():
                self.dump_datasets_worker()

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
            raise AssertionError('Config filename %r does not exist.' % self.filename)
        fileConfig(self.filename)
        conf = appconfig('config:' + self.filename)

    def delete_vocabulary(self, name):
        registry = LocalCKAN()
        vocab = registry.action.vocabulary_show(id=name)
        for t in vocab['tags']:
            registry.action.tag_delete(id=t['id'])
        registry.action.vocabulary_delete(id=vocab['id'])

    def create_vocabulary(self, name, terms):
        registry = LocalCKAN()
        try:
            vocab = registry.action.vocabulary_show(id=name)
            print "{name} vocabulary exists, skipping".format(name=name)
            return
        except NotFound:
            pass
        print 'creating {name} vocabulary'.format(name=name)
        vocab = registry.action.vocabulary_create(name=name)
        for term in terms:
            # don't create items that only existed in pilot
            if 'id' not in term:
                continue
            registry.action.tag_create(
                name=term['key'],
                vocabulary_id=vocab['id'],
                )

    def load_datasets(self, jl_source, start_line=1, max_count=None):
        start_line = int(start_line)
        if max_count is not None:
            max_count = int(max_count)

        log = None
        if self.options.log:
            log = open(self.options.log, 'a')

        def line_reader():
            if self.options.gzip:
                source_file = gzip.GzipFile(jl_source)
            else:
                source_file = open(jl_source)
            for num, line in enumerate(source_file, 1):
                if num < start_line:
                    continue
                if max_count is not None and num >= start_line + max_count:
                    break
                yield num, line.strip()
        cmd = [sys.argv[0], 'canada', 'load-dataset-worker',
            '-c', self.options.config]
        if self.options.ckan_user:
            cmd += ['-u', self.options.ckan_user]
        if self.options.replace_datasets:
            cmd += ['-r']

        stats = completion_stats(self.options.processes)
        pool = worker_pool(cmd, self.options.processes, line_reader())
        with _quiet_int_pipe():
            for job_ids, finished, result in pool:
                timestamp, action, error, response = json.loads(result)
                print job_ids, stats.next(), finished, action,
                print json.dumps(response) if response else ''
                if log:
                    log.write(json.dumps([
                        timestamp,
                        finished,
                        action,
                        error,
                        response,
                        ]) + '\n')
                    log.flush()

    def load_dataset_worker(self):
        """
        a process that accepts lines of json on stdin which is parsed and
        passed to the package_create action.  it produces lines of json
        which are the responses from each action call.
        """
        registry = LocalCKAN(self.options.ckan_user, {'return_id_only': True})

        def reply(action, error, response):
            sys.stdout.write(json.dumps([
                datetime.now().isoformat(),
                action,
                error,
                response]) + '\n')

        for line in iter(sys.stdin.readline, ''):
            try:
                pkg = json.loads(line)
            except UnicodeDecodeError, e:
                pkg = None
                reply('read', 'UnicodeDecodeError', unicode(e))

            if pkg:
                validation_override = pkg.get('validation_override') # FIXME: remove me
                _trim_package(pkg)

                existing = None
                if self.options.replace_datasets:
                    try:
                        existing = registry.action.package_show(id=pkg['id'])
                        _trim_package(existing)
                    except NotFound:
                        existing = None
                    if existing == pkg:
                        reply('unchanged', None, None)
                        pkg = None

            if pkg:
                pkg['validation_override'] = validation_override
                action = 'replace' if existing else 'create'
                try:
                    if existing:
                        response = registry.action.package_update(**pkg)
                    else:
                        response = registry.action.package_create(**pkg)
                except ValidationError, e:
                    reply(action, 'ValidationError', e.error_dict)
                except SearchIndexError, e:
                    reply(action, 'SearchIndexError', unicode(e))
                else:
                    reply(action, None, response)
            sys.stdout.flush()

    def portal_update(self, source, activity_date=None):
        """
        collect batches of package ids modified at source since activity_date
        and apply the package updates to the local CKAN instance for all
        packages with published_date set to any time in the past.
        """
        if activity_date:
            # XXX local time :-(
            activity_date = isodate(activity_date, None)
        else:
            activity_date = datetime.now() - timedelta(days=7)

        seen_package_id_set = set()

        def changed_package_id_runs(start_date):
            while True:
                package_ids, next_date = self._changed_package_ids_since(
                    source, start_date, seen_package_id_set)
                if next_date is None:
                    return
                yield package_ids, next_date
                start_date = next_date

        cmd = [sys.argv[0], 'canada', 'portal-update-worker', source,
             '-c', self.options.config]
        if self.options.push_apikey:
            cmd.extend(['-a', self.options.push_apikey])
        pool = worker_pool(
            cmd,
            self.options.processes,
            [],
            stop_when_jobs_done=False,
            stop_on_keyboard_interrupt=False,
            )
        pool.next() # advance generator so we may call send() below

        with _quiet_int_pipe():
            for package_ids, next_date in changed_package_id_runs(activity_date):
                stats = dict(created=0, updated=0, deleted=0, unchanged=0)

                job_ids, finished, result = pool.send(enumerate(package_ids))
                while result is not None:
                    stats[result.strip()] += 1
                    job_ids, finished, result = pool.next()

                print next_date.isoformat(),
                print " ".join("%s:%s" % kv for kv in sorted(stats.items()))

    def _changed_package_ids_since(self, source, since_time, seen_id_set=None):
        """
        Query source ckan instance for packages changed since_time.
        returns (package ids, next since_time to query) or (None, None)
        when no more changes are found.

        source - URL of CKAN source, e.g. 'http://registry.statcan.gc.ca'
        since_time - local datetime to start looking for changes
        seen_id_set - set of package ids already processed, this set is
                      modified by calling this function

        If all the package ids found were included in seen_id_set this
        function will return an empty list of package ids.  Note that
        this is different than when no more changes found and (None, None)
        is returned.
        """
        remote = RemoteCKAN(source)
        data = remote.action.changed_packages_activity_list_since(
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


    def portal_update_worker(self, remote):
        """
        a process that accepts package ids on stdin which are passed to
        the package_show API on the remote CKAN instance and compared
        to the local version of the same package.  The local package is
        then created, updated, deleted or left unchanged.  This process
        outputs that action as a string 'created', 'updated', 'deleted'
        or 'unchanged'
        """
        if self.options.push_apikey:
            registry = LocalCKAN()
            portal = RemoteCKAN(remote, apikey=self.options.push_apikey)
        else:
            registry = RemoteCKAN(remote)
            portal = LocalCKAN()
        now = datetime.now()

        for package_id in iter(sys.stdin.readline, ''):
            try:
                source_pkg = registry.action.package_show(id=package_id.strip())
            except NotAuthorized:
                source_pkg = None

            _trim_package(source_pkg)

            if source_pkg and not self.options.mirror:
                # treat unpublished packages same as deleted packages
                if not source_pkg['portal_release_date'] or isodate(
                        source_pkg['portal_release_date'], None) > now:
                    source_pkg = None

            try:
                # don't pass user in context so deleted packages
                # raise NotAuthorized
                target_pkg = portal.call_action('package_show',
                    {'id':package_id.strip()}, {})
            except (NotFound, NotAuthorized):
                target_pkg = None

            _trim_package(target_pkg)

            if target_pkg is None and source_pkg is None:
                result = 'unchanged'
            elif target_pkg is None:
                # CREATE
                portal.action.package_create(**source_pkg)
                result = 'created'
            elif source_pkg is None:
                # DELETE
                portal.action.package_delete(id=package_id.strip())
                result = 'deleted'
            elif source_pkg == target_pkg:
                result = 'unchanged'
            else:
                # UPDATE
                portal.action.package_update(**source_pkg)
                result = 'updated'

            sys.stdout.write(result + '\n')
            sys.stdout.flush()


    def create_organization(self, org):
        registry = LocalCKAN()
        titles = [org[l] for l in schema_description.languages]
        titles = [titles[0]] + [t for t in titles[1:] if t != titles[0]]
        kwargs = {
            'name':org['key'],
            'title':u' | '.join(titles),
            'extras':[{'key': 'department_number',
                'value': unicode(org['id'])}],
            }
        if 'pilot_uuid' in org:
            kwargs['id'] = org['pilot_uuid']
        try:
            response = registry.action.organization_show(id=kwargs['name'])
        except NotFound:
            registry.action.organization_create(**kwargs)
        else:
            if response['title'] != kwargs['title']:
                registry.action.organization_update(id=response['id'], **kwargs)

    def delete_organization(self, org):
        registry = LocalCKAN()
        try:
            organization = registry.action.organization_show(id=org['id'].lower())
            response = registry.action.group_delete(id=organization['id'])
        except NotFound:
            pass


    def dump_datasets(self):
        """
        Output all public datasets as a .jl file
        """
        registry = LocalCKAN('visitor')
        package_names = registry.action.package_list()

        cmd = [sys.argv[0], 'canada', 'dump-datasets-worker',
            '-c', self.options.config]
        stats = completion_stats(self.options.processes)
        pool = worker_pool(cmd, self.options.processes,
            enumerate(package_names))

        sink = sys.stdout
        if self.options.gzip:
            sink = gzip.GzipFile(fileobj=sys.stdout, mode='wb')
        expecting_number = 0
        results = {}
        with _quiet_int_pipe():
            for job_ids, finished, result in pool:
                sys.stderr.write("%s %s %s\n" % (
                    job_ids, stats.next(), finished))
                results[finished] = result
                # keep the output in the same order as package_names
                while expecting_number in results:
                    sink.write(results.pop(expecting_number))
                    expecting_number += 1

    def dump_datasets_worker(self):
        """
        a process that accepts package names, one per line, and outputs
        lines of json containing that package data.
        """
        registry = LocalCKAN('visitor')

        for name in iter(sys.stdin.readline, ''):
            sys.stdout.write(json.dumps(
                registry.action.package_show(id=name.strip()), sort_keys=True)
                + '\n')
            sys.stdout.flush()


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
            'maintainer_email', 'author',
            'groups', # just because we don't use them
            'relationships_as_subject', 'department_number',
            # FIXME: remove these when we can:
            'validation_override', 'resource_type',
            ]:
        if k in pkg:
            del pkg[k]
    for r in pkg['resources']:
        for k in ['resource_group_id', 'revision_id',
                'revision_timestamp', 'cache_last_updated',
                'webstore_last_updated', 'id', 'state', 'hash',
                'description', 'tracking_summary', 'mimetype_inner',
                'mimetype', 'cache_url', 'created', 'webstore_url',
                'last_modified', 'position', ]:
            if k in r:
                del r[k]
        for k in ['name', 'size']:
            if k not in r:
                r[k] = None
    for k in ['ready_to_publish', 'private']:
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
        elif field['type'] == 'tag_vocabulary' and not isinstance(
                pkg.get(name), list):
            pkg[name] = convert_pilot_uuid_list(field)(pkg.get(name, []))
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
