from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic import get_action, NotFound, ValidationError
from ckan.logic.validators import isodate
import paste.script
from paste.script.util.logging_config import fileConfig

import os
import re
import json
import time
import sys
import urllib2
from datetime import datetime, timedelta

from ckanext.canada.metadata_schema import schema_description
from ckanext.canada.workers import worker_pool

class CanadaCommand(CkanCommand):
    """
    CKAN Canada Extension

    Usage::

        paster canada create-vocabularies [-c <path to config file>]
                      delete-vocabularies
                      create-organizations
                      load-datasets <ckan user> <.jl source>
                                    [<lines to skip> [<lines to load>]]
                                    [-p <processes>]
                      portal-update <registry server> [<last activity date>]
                                    [-p <processes>]

        * processes defaults to 1
        * last activity date defaults to 7 days ago
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
    parser.add_option('-p', '--processes', dest='processes',
        default=1, type="int")

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
            for org in schema_description.dataset_field_by_id['author']['choices']:
                if 'id' not in org:
                    continue
                self.create_organization(org)

        elif cmd == 'delete-organizations':
            raise NotImplementedError(
                "Sorry, this can't be implemented properly until group "
                "purging is implemented in CKAN")
            for org in schema_description.dataset_field_by_id['author']['choices']:
                if 'id' not in org:
                    continue
                self.delete_organization(org)

        elif cmd == 'load-datasets':
            self.load_datasets(self.args[1], self.args[2], *self.args[3:])
        
        elif cmd == 'load-dataset-worker':
            self.load_dataset_worker(self.args[1])

        elif cmd == 'load-random-datasets':
            self.load_rando(self.args[1])

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
        user = get_action('get_site_user')({'ignore_auth': True}, ())
        context = {'user': user['name']}
        vocab = get_action('vocabulary_show')(context, {'id': name})
        for t in vocab['tags']:
            get_action('tag_delete')(context, {'id': t['id'],})
        get_action('vocabulary_delete')(context, {'id': vocab['id']})

    def create_vocabulary(self, name, terms):
        user = get_action('get_site_user')({'ignore_auth': True}, ())
        context = {'user': user['name']}
        try:
            vocab = get_action('vocabulary_show')(context, {'id': name})
            print "{name} vocabulary exists, skipping".format(name=name)
            return
        except NotFound:
            pass
        print 'creating {name} vocabulary'.format(name=name)
        vocab = get_action('vocabulary_create')(context, {'name': name})
        for term in terms:
            # don't create items that only existed in pilot
            if 'id' not in term:
                continue
            get_action('tag_create')(context, {
                'name': term['key'],
                'vocabulary_id': vocab['id'],
                })

    def load_datasets(self, username, jl_source, skip_lines=0, max_count=None):
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

        pool = worker_pool(
            [sys.argv[0], 'canada', 'load-dataset-worker', username],
            self.options.processes,
            line_reader(),
            )

        for job_ids, finished, result in pool:
            print job_ids, finished, result.strip()


    def load_dataset_worker(self, username):
        """
        a process that accepts lines of json on stdin which is parsed and
        passed to the package_create action.  it produces lines of json
        which are the responses from each action call.
        """
        for line in iter(sys.stdin.readline, ''):
            context = {'user': username, 'return_id_only': True}
            pkg = json.loads(line)
            try:
                response = get_action('package_create')(context, pkg)
            except ValidationError, e:
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
        # local time :-(
        if activity_date:
            activity_date = isodate(activity_date, None)
        else:
            activity_date = datetime.now() - timedelta(days=7)
        print self._changed_package_ids_since(source, activity_date)


    def _changed_package_ids_since(self, source, since_time):
        """
        Query source ckan instance for packages changed since_time.
        returns (package ids, next since_time to query)
        """
        url = source + '/api/action/changed_packages_activity_list_since'
        data = json.dumps({
            'since_time': since_time.isoformat(),
            })
        header = {'Content-Type': 'application/json'}
        req = urllib2.Request(url, data, headers=header)
        data = json.loads(urllib2.urlopen(req).read())

        id_set = set()
        package_ids = []
        for result in data['result']:
            package_id = result['data']['package']['id']
            if package_id in id_set:
                continue
            id_set.add(package_id)
            package_ids.append(package_id)

        if data['result']:
            since_time = data['result'][-1]['timestamp']

        return package_ids, since_time


    def load_rando(self, username):
        count = 0
        total = 0.0
        import random
        log = file('rando.log', 'a')

        while True:
            try:
                print str(count) + ",",
                log.write(str(count) + ",")
                start = time.time()
                context = {'user': username}
                response = get_action('package_create')(context, {
                    'name': "%x" % random.getrandbits(64),
                    'maintainer': '',
                    'title': '',
                    'author_email': '',
                    'notes': '',
                    'author': '',
                    'maintainer_email': '',
                    'license_id': ''})
            except ValidationError, e:
                print unicode(e).encode('utf-8')
            except KeyboardInterrupt:
                return
            else:
                end = time.time()
                count += 1
                total += end - start
                log.write("%f\n" % (end - start,))
                log.flush()
                print "%f, %f" % (end - start, total / count)

    def create_organization(self, org):
        organization = {
            'name':org['id'].lower(),
            'title':org['id'],
            'description':org['key'],
            }
        user = get_action('get_site_user')({'ignore_auth': True}, ())
        context = {'user': user['name']}
        try:
            response = get_action('organization_create')(context, organization)
        except ValidationError, e:
            print organization['name'], unicode(e).encode('utf-8')

    def delete_organization(self, org):
        user = get_action('get_site_user')({'ignore_auth': True}, ())
        context = {'user': user['name']}
        try:
            organization = get_action('organization_show')(context, {
                'id':org['id'].lower()})
            response = get_action('group_delete')(context, organization)
        except NotFound:
            pass
