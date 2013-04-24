from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic.validators import isodate
import paste.script
from paste.script.util.logging_config import fileConfig

import os
import json
import time
import sys
from datetime import datetime, timedelta

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.workers import worker_pool
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
                                    [<lines to skip> [<lines to load>]]
                                    [-p <processes>] [-u <ckan user>]
                      portal-update <registry server> [<last activity date>]
                                    [-p <processes>]

        * all commands take optional [-c <path to ckan config file>]
        * <processes> defaults to 1
        * <last activity date> defaults to 7 days ago
        * <ckan user> defaults to the system user
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
    parser.add_option('-p', '--processes', dest='processes',
        default=1, type="int")
    parser.add_option('-u', '--ckan-user', dest='ckan_user',
        default=None)

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
            self.load_dataset_worker()

        elif cmd == 'portal-update':
            self.portal_update(self.args[1], *self.args[2:])

        elif cmd == 'portal-update-worker':
            self.portal_update_worker(self.args[1])

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

    def load_datasets(self, jl_source, skip_lines=0, max_count=None):
        skip_lines = int(skip_lines)
        if max_count is not None:
            max_count = int(max_count)

        def line_reader():
            for num, line in enumerate(open(jl_source)):
                if num < skip_lines:
                    continue
                if max_count is not None and num >= skip_lines + max_count:
                    break
                yield num, line
        cmd = [sys.argv[0], 'canada', 'load-dataset-worker',
            '-c', self.options.config]
        if self.options.ckan_user:
            cmd += ['-u', self.options.ckan_user]

        pool = worker_pool(cmd, self.options.processes, line_reader())
        for job_ids, finished, result in pool:
            print job_ids, finished, result.strip()


    def load_dataset_worker(self):
        """
        a process that accepts lines of json on stdin which is parsed and
        passed to the package_create action.  it produces lines of json
        which are the responses from each action call.
        """
        registry = LocalCKAN(self.options.ckan_user, {'return_id_only': True})
        for line in iter(sys.stdin.readline, ''):
            pkg = json.loads(line)
            try:
                response = registry.action.package_create(**pkg)
            except (ValidationError, SearchIndexError), e:
                sys.stdout.write(unicode(e).encode('utf-8') + '\n')
            except KeyboardInterrupt:
                return
            else:
                sys.stdout.write(response + '\n')
            try:
                sys.stdout.flush()
            except IOError:
                break

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

        pool = worker_pool(
            [sys.argv[0], 'canada', 'portal-update-worker', source,
             '-c', self.options.config],
            self.options.processes,
            [],
            stop_when_jobs_done=False,
            stop_on_keyboard_interrupt=False,
            )
        pool.next() # advance generator so we may call send() below

        for package_ids, next_date in changed_package_id_runs(activity_date):
            stats = dict(created=0, updated=0, deleted=0, unchanged=0)

            jobs = ((i, i + '\n') for i in package_ids)
            try:
                job_ids, finished, result = pool.send(jobs)
                while result is not None:
                    stats[result.strip()] += 1
                    job_ids, finished, result = pool.next()
            except KeyboardInterrupt:
                break

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

        if not data['result']:
            return None, None

        package_ids = []
        for result in data['result']:
            package_id = result['data']['package']['id']
            if package_id in seen_id_set:
                continue
            seen_id_set.add(package_id)
            package_ids.append(package_id)

        if data['result']:
            since_time = isodate(data['result'][-1]['timestamp'], None)

        return package_ids, since_time


    def portal_update_worker(self, source):
        """
        a process that accepts package ids on stdin which are passed to
        the package_show API on the remote CKAN instance and compared
        to the local version of the same package.  The local package is
        then created, updated, deleted or left unchanged.  This process
        outputs that action as a string 'created', 'updated', 'deleted'
        or 'unchanged'
        """
        registry = RemoteCKAN(source)
        portal = LocalCKAN()
        now = datetime.now()

        def trim_package(pkg):
            """
            remove keys from pkg that we don't care about when comparing
            or updating/creating packages.
            """
            if not pkg:
                return
            for k in ['extras', 'metadata_modified', 'metadata_created',
                    'revision_id', 'revision_timestamp']:
                del pkg[k]
            for t in pkg.get('tags', []):
                for k in ['id', 'revision_timestamp']:
                    del t[k]
            for r in pkg['resources']:
                for k in ['resource_group_id', 'revision_id',
                        'revision_timestamp']:
                    del r[k]

        for package_id in iter(sys.stdin.readline, ''):
            try:
                data = registry.action.package_show(id=package_id.strip())
                source_pkg = data['result']
            except NotAuthorized:
                source_pkg = None

            trim_package(source_pkg)

            if source_pkg:
                # treat unpublished packages same as deleted packages
                if not source_pkg['date_published'] or isodate(
                        source_pkg['date_published'], None) > now:
                    source_pkg = None

            try:
                # don't pass user in context so deleted packages
                # raise NotAuthorized
                target_pkg = portal.call_action('package_show',
                    {'id':package_id.strip()}, {})
            except (NotFound, NotAuthorized):
                target_pkg = None

            trim_package(target_pkg)

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
            try:
                sys.stdout.flush()
            except IOError:
                break


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
        registry.action.organization_create(**kwargs)

    def delete_organization(self, org):
        registry = LocalCKAN()
        try:
            organization = registry.action.organization_show(id=org['id'].lower())
            response = registry.action.group_delete(id=organization['id'])
        except NotFound:
            pass
