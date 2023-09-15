# -*- coding: utf-8 -*-
import sys
import os
from unicodecsv import DictReader
from ckan.plugins.toolkit import config
from ckanext.recombinant.tables import get_geno, get_dataset_types

BATCH_SIZE = 1000
MONTHS_FR = [
    u'', # "month 0"
    u'janvier',
    u'février',
    u'mars',
    u'avril',
    u'mai',
    u'juin',
    u'juillet',
    u'août',
    u'septembre',
    u'octobre',
    u'novembre',
    u'décembre',
    ]

def solr_connection(ini_prefix, solr_url=None):
    """
    Set up solr connection
    :param ini_prefix: prefix to use in specifying .ini file keys (e.g.,
        ati_summaries to use config setting ati_summaries.solr_url etc.)
    :ptype ini_prefix: str

    :return a solr connection from configured URL, user, password settings
    :rtype object
    """
    from pysolr import Solr
    if not solr_url:
        url = config.get('{0:s}.solr_url'.format(ini_prefix))
        user = config.get('{0:s}.solr_user'.format(ini_prefix))
        password = config.get('{0:s}.solr_password'.format(ini_prefix))
    else:
        url = solr_url
        user = None
        password = None
    if url is None:
        raise KeyError('{0:s}.solr_url'.format(ini_prefix))
    if user is not None and password is not None:
        return Solr(url, http_user=user, http_pass=password)
    return Solr(url)

def data_batch(org_id, lc, dataset_type):
    """
    Generator of dataset dicts for organization with name org

    :param org_id: the id for the organization of interest
    :ptype org_id: str
    :param lc: local CKAN
    :ptype lc: obj
    :param dataset_type: e.g., 'ati', 'pd', etc.
    :ptype dataset_type: str

    generates (resource name, batch of records) tuples
    """
    result = lc.action.package_search(
        q="type:{0:s} owner_org:{1:s}".format(dataset_type, org_id),
        rows=2)['results']
        
    if not result:
        return
    if len(result) != 1:
       sys.stderr.write('1 record expected for %s %s, found %d' %
            (dataset_type, org_id, len(result)))

    dataset = result[0]
    for resource in dataset['resources']:
        offset = 0
        while True:
            rval = lc.action.datastore_search(
                resource_id=resource['id'],
                limit=BATCH_SIZE,
                offset=offset)
            records = rval['records']
            if not records:
                break
            offset += len(records)
            yield (resource['name'], records)

_REMOVE_CONTROL_CODES = dict((x, None) for x in range(32) if x != 10 and x != 13)

def safe_for_solr(s):
    """
    return a string that is safe for solr to ingest by removing all
    control characters except for CR and LF
    """
    if s is None:
        return u''
    assert isinstance(s, unicode)
    return s.translate(_REMOVE_CONTROL_CODES)
