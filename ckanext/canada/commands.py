from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic import get_action, NotFound, ValidationError

import re
import json
import time

from ckanext.canada.metadata_schema import schema_description

class CanadaCommand(CkanCommand):
    """
    CKAN Canada Extension

    Usage::

        paster canada create-vocabularies [-c <path to config file>]
                      delete-vocabularies
                      create-organizations
                      load-datasets <ckan user> <.jl source>
                                    [<lines to skip> [<lines to load>]]
                      load-random-datasets <ckan user>
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

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
            try:
                self.load_datasets(self.args[1], self.args[2], *self.args[3:])
            except KeyboardInterrupt:
                # this will happen a lot while we work on performance
                pass

        elif cmd == 'load-random-datasets':
            try:
                self.load_rando(self.args[1])
            except KeyboardInterrupt:
                # this will happen a lot while we work on performance
                pass
        else:
            print self.__doc__

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
        count = 0
        total = 0.0

        for num, line in enumerate(open(jl_source)):
            if num < skip_lines:
                continue
            if max_count is not None and count >= max_count:
                break
            print "line %d:" % num,
            try:
                start = time.time()
                context = {'user': username, 'return_id_only': True}
                pkg = json.loads(line)
                response = get_action('package_create')(context, pkg)
            except ValidationError, e:
                print str(e)
            else:
                end = time.time()
                count += 1
                total += end - start
                print "%f seconds, %f average" % (end - start, total / count)

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

