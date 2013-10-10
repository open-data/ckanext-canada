
import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand

from ckanapi import LocalCKAN

class ATICommand(CkanCommand):
    """
    Manage the ATI Summaries SOLR index

    Usage::

        paster ati clear
                   rebuild
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')

    def command(self):
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'clear':
            return self._clear_index()
        elif cmd == 'rebuild':
            return self._rebuild()

    def _clear_index(self):
        conn = _solr_connection()
        conn.delete_query("*:*")
        conn.commit()

    def _rebuild(self):
        conn = _solr_connection()
        lc = LocalCKAN()
        for org in lc.action.organization_list():
            g = _ati_summaries(org, lc)

            print org, len(list(g))
        #rval = conn.query("*:*" , rows=2)

def _solr_connection():
    from solr import SolrConnection
    url = config['ati_summaries.solr_url']
    user = config.get('ati_summaries.solr_user')
    password = config.get('ati_summaries.solr_password')
    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    return SolrConnection(url)

def _ati_summaries(org, lc):
    """
    generator of ati summary dicts for organization with name org
    """
    resource_alias = 'ati-summaries-{0}'.format(org)
    offset = 0
    while True:
        rval = lc.action.datastore_search(resource_id=resource_alias,
            limit=1000, offset=offset)
        records = rval['records']
        if not records:
            return
        for r in records:
            yield r
        offset += len(records)
