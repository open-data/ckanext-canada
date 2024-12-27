# -*- coding: utf-8 -*-

# NOTE: used to connect to the SOLR cores for Drupal PD Searches
# TODO: remove once all PDs are in Django

from typing import Optional, Union, Generator, Tuple, List, Any

import sys
from pysolr import Solr
from ckan.plugins.toolkit import config
from ckanapi import LocalCKAN

BATCH_SIZE = 1000
MONTHS_FR = [
    '',  # "month 0"
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre',
]


def solr_connection(ini_prefix: str,
                    solr_url: Optional[Union[str, None]] = None) -> Solr:
    """
    Set up solr connection
    :param ini_prefix: prefix to use in specifying .ini file keys (e.g.,
        ati_summaries to use config setting ati_summaries.solr_url etc.)
    :ptype ini_prefix: str

    :return a solr connection from configured URL, user, password settings
    :rtype object
    """
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
        # type_ignore_reason: solr user pass may be required for Drupal PD searches
        return Solr(url, http_user=user, http_pass=password)  # type: ignore
    return Solr(url)


def data_batch(org_id: str, lc: LocalCKAN,
               dataset_type: str) -> Generator[Tuple[str, List[Any]]]:
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


def safe_for_solr(s: str) -> str:
    """
    return a string that is safe for solr to ingest by removing all
    control characters except for CR and LF
    """
    if s is None:
        return ''
    assert isinstance(s, str)
    return s.translate(_REMOVE_CONTROL_CODES)
