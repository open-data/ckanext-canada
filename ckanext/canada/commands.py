from ckan import model
from ckan.lib.cli import CkanCommand
from ckan.logic import get_action, NotFound

import logging
import re

from ckanext.canada.metadata_schema import schema_description

class CanadaCommand(CkanCommand):
    """
    CKAN Canada Extension

    Usage::

        paster canada create-vocabularies [-c <path to config file>]
                      delete-vocabularies
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

        if cmd == 'create-vocabularies':
            for name, terms in schema_description.vocabularies.iteritems():
                self.create_vocabulary(name, terms)

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
            logging.info("{name} vocabulary exists, skipping".format(name=name))
            return
        except NotFound:
            pass
        logging.info('creating {name} vocabulary'.format(name=name))
        vocab = get_action('vocabulary_create')(context, {'name': name})
        for term in terms:
            get_action('tag_create')(context, {
                'name': term['key'],
                'vocabulary_id': vocab['id'],
                })

