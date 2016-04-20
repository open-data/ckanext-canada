# -*- coding: utf-8 -*-
import os
from unicodecsv import DictReader
from pylons import config
from ckanext.recombinant.tables import get_chromo, get_geno, get_dataset_types

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

def solr_connection(ini_prefix):
    """
    Set up solr connection
    :param ini_prefix: prefix to use in specifying .ini file keys (e.g.,
        ati_summaries to use config setting ati_summaries.solr_url etc.)
    :ptype ini_prefix: str

    :return a solr connection from configured URL, user, password settings
    :rtype object
    """
    from solr import SolrConnection
    url = config.get('{0:s}.solr_url'.format(ini_prefix))
    user = config.get('{0:s}.solr_user'.format(ini_prefix))
    password = config.get('{0:s}.solr_password'.format(ini_prefix))
    if url is None:
        raise KeyError('{0:s}.solr_url'.format(ini_prefix))
    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    return SolrConnection(url)

def data_batch(org_id, lc, target_dataset):
    """
    Generator of dataset dicts for organization with name org

    :param org_id: the id for the organization of interest
    :ptype org_id: str
    :param lc: local CKAN
    :ptype lc: obj
    :param target_dataset: name of target dataset (e.g., 'ati', 'pd', etc.)
    :ptype target_dataset: str

    :return generates batches of dataset dict records
    :rtype batch of dataset dict records
    """
    dataset_types = get_dataset_types()
    for dataset_type in dataset_types:
        geno = get_geno(dataset_type)
        if geno.get('target_dataset') == target_dataset:
            break
    else:
        return

    result = lc.action.package_search(
        q="type:{0:s} owner_org:{1:s}".format(dataset_type, org_id),
        rows=2)['results']
        
    if not result:
        return
    assert len(result) == 1, result

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
            yield records


def csv_data_batch(csv_path, target_dataset):
    """
    Generator of dataset records from csv file

    :param csv_path: file to parse

    :return a batch of records for at most one organization
    :rtype: dict mapping at most one org-id to
            at most BATCH_SIZE (dict) records
    """
    records = []
    current_owner_org = None

    firstpart, filename = os.path.split(csv_path)
    assert filename.endswith('.csv')

    chromo = get_chromo(filename[:-4])
    assert chromo['target_dataset'] == target_dataset

    with open(csv_path) as f:
        csv_in = DictReader(f)
        cols = csv_in.unicode_fieldnames

        expected = [f['datastore_id'] for f in chromo['fields']]
        assert cols[:-2] == expected, 'column mismatch:\n{0}\n{1}'.format(
            cols[:-2], expected)

        for row_dict in csv_in:
            owner_org = row_dict.pop('owner_org')
            owner_org_title = row_dict.pop('owner_org_title')
            if owner_org != current_owner_org:
                if records:
                    yield (current_owner_org, records)
                records = []
                current_owner_org = owner_org

            row_dict = dict((k, safe_for_solr(v)) for k, v in row_dict.items())
            records.append(row_dict)
            if len(records) >= BATCH_SIZE:
                yield (current_owner_org, records)
                records = []
    if records:
        yield (current_owner_org, records)


_REMOVE_CONTROL_CODES = dict((x, None) for x in range(32) if x != 10 and x != 13)

def safe_for_solr(s):
    """
    return a string that is safe for solr to ingest by removing all
    control characters except for CR and LF
    """
    assert isinstance(s, unicode)
    return s.translate(_REMOVE_CONTROL_CODES)
