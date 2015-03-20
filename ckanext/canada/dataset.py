# -*- coding: utf-8 -*-
import os
from unicodecsv import DictReader
from pylons import config
from ckanext.recombinant.plugins import get_table

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

def solr_connection(ini_prefix, solr_default=False):
    """
    Set up solr connection
    :param ini_prefix: prefix to use in specifying .ini file keys (e.g.,
        ati_summaries to use config setting ati_summaries.solr_url etc.)
    :ptype ini_prefix: str
    :param solr_default: whether to accept .ini file keys for solr if
        ini_prefix-specified settings are absent
    :ptype solr_default: true

    :return a solr connection from configured URL, user, password settings
    :rtype object
    """
    from solr import SolrConnection
    url = config.get('{0:s}.solr_url'.format(ini_prefix))
    user = config.get('{0:s}.solr_user'.format(ini_prefix))
    password = config.get('{0:s}.solr_password'.format(ini_prefix))
    if solr_default:
        if not url:
            url = config.get('solr_url')
        if not user:
            user = config.get('solr_user')
        if not password:
            password = config.get('solr_password')
    if url is None:
        raise KeyError('{0:s}.solr_url'.format(ini_prefix))
    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    return SolrConnection(url)

def data_batch(org_id, lc, dataset_types):
    """
    Generator of dataset dicts for organization with name org

    :param org_id: the id for the organization of interest
    :ptype org_id: str
    :param lc: local CKAN
    :ptype lc: obj
    :param dataset_types: dataset types of interest
    :ptype dataset_types: sequence of str

    :return generates batches of dataset dict records
    :rtype batch of dataset dict records
    """
    for dataset_type in dataset_types:
        records = {}
        result = lc.action.package_search(
            q="type:{0:s} owner_org:{1:s}".format(dataset_type, org_id),
            rows=1000)['results']
        print ">>> " + org_id + ": " + str(len(result))
        if len(result) == 0:
            yield records
        else:
            resource_id = result[0]['resources'][0]['id']
            offset = 0
            while True:
                rval = lc.action.datastore_search(
                    resource_id=resource_id,
                    limit=BATCH_SIZE,
                    offset=offset)
                records = rval['records']
                if not records:
                    break
                yield records
                offset += len(records)


def csv_data_batch(csv_path, dataset_types):
    """
    Generator of dataset records from csv file

    :param csv_path: file to parse
    :ptype csv_file: str
    :param dataset_types: dataset types of interest as per JSON schema
    :ptype dataset_types: sequence of basestr

    :return a batch of records for at most one organization
    :rtype: dict mapping at most one org-id to
            at most BATCH_SIZE (dict) records
    """
    # Use JSON schema to discover the dataset type to which the file corresponds
    schema_tables = dict((
            t,
            dict((f['label'], f['datastore_id'])
                for f in get_table(t)['fields']))
        for t in dataset_types)
    records = {}
    schema_cols = None
    cols = None
    csv_path = os.path.abspath(os.path.expandvars(os.path.expanduser(csv_path)))
    if os.path.islink(csv_path):
        csv_path = os.readlink(csv_path)
    with open(csv_path) as f:
        csv_in = DictReader(f)
        cols = csv_in.unicode_fieldnames

        for k, v in schema_tables.iteritems():
            if (len(set(v.keys()).intersection(set(cols))) == len(v.keys()) and
                    len(cols) == len(v.keys()) + 2):
                # columns represent all schema data fields + 'Org id', 'Org'
                schema_cols = [v[col] if col in v else col for col in cols]
                break

    assert schema_cols > 0, '{0:s} does not match any dataset type {1}'.format(
        csv_path, dataset_types)

    with open(csv_path) as f:
        # use new dict, each col named for its corresponding JSON datastore_id
        csv_in = DictReader(f, fieldnames=schema_cols)
        csv_in.next()   # skip header row: no new info
        for row_dict in csv_in:
            org_id = row_dict.pop('Org id')
            org = row_dict.pop('Org')
            if org_id not in records:
                if len(records.keys()):
                    org_id_done = records.keys()[0]
                    yield {org_id_done: records.pop(org_id_done)}
                records[org_id] = []
            records[org_id].append(row_dict)
            if len(records[org_id]) >= BATCH_SIZE:
                yield {org_id: records.pop(org_id)}
    yield records
