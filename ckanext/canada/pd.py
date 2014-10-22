# -*- coding: utf-8 -*-
import os
import hashlib
import calendar
import datetime
from unicodecsv import DictReader

import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand

from ckanapi import LocalCKAN, NotFound

from ckanext.recombinant.write_xls import xls_template
from ckanext.recombinant.plugins import get_table

BATCH_SIZE = 1000
DATASET_TYPE = 'proactive-disclosure'
SPLIT_XLS_ROWS = 50002

MONTHS_FRA = [
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

class PDCommand(CkanCommand):
    """
    Manage the Proactive Disclosures SOLR index / data files

    Usage::

        paster pd build-templates <sources> <dest-dir>
                  clear
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

        if cmd == 'build-templates':
            return self._build_templates()
        elif cmd == 'clear':
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
            count = 0
            org_detail = lc.action.organization_show(id=org)
            for records in _proactive_disclosure(org_detail, lc):
                _update_records(records, org_detail, conn)
                count += len(records)

            print org, count

    def _build_templates(self):
        lc = LocalCKAN()
        output_files = {}
        next_row = {}
        output_counter = {}
        output_path = self.args[2:][-1]
        table = get_table(DATASET_TYPE)

        def close_write_file(org_id):
            book = output_files[org_id]
            if not book:
                return
            book.save(os.path.join(output_path,
                org_id + '-' + str(output_counter[org_id]) + '.xls'))
            output_files[org_id] = None

        def out_file(org_id):
            if org_id in output_files:
                next_row[org_id] += 1
                # need to start a new file?
                if next_row[org_id] > SPLIT_XLS_ROWS:
                    close_write_file(org_id)
                else:
                    return output_files[org_id], next_row[org_id]
            try:
                org = lc.action.organization_show(id=org_id, include_datasets=False)
            except NotFound:
                print 'org id', org_id, 'not found'
                output_files[org_id] = None
                next_row[org_id] = 0
                return None, None
            book = xls_template(DATASET_TYPE, org)
            output_files[org_id] = book
            output_counter[org_id] = output_counter.get(org_id, 0) + 1
            next_row[org_id] = len(book.get_sheet(0).get_rows())
            return book, next_row[org_id]

        def add_row(book, row, d):
            sheet = book.get_sheet(0)
            for i, f in enumerate(table['fields']):
                sheet.write(row, i, d[f['datastore_id']])

        for f in self.args[1:-1]:
            for d in DictReader(open(f, 'rb')):
                book, row = out_file(d['organization'])
                if not book:
                    continue
                add_row(book, row, d)

        for org_id in output_files:
            close_write_file(org_id)


def _solr_connection():
    from solr import SolrConnection
    url = config['proactive_disclosure.solr_url']
    user = config.get('proactive_disclosure.solr_user')
    password = config.get('proactive_disclosure.solr_password')
    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    return SolrConnection(url)

def _proactive_disclosure(org, lc):
    """
    generator of ati summary dicts for organization with name org
    """
    result = lc.action.package_search(
        q="type:%s owner_org:%s" % (DATASET_TYPE, org['id']),
        rows=1000)['results']
    resource_id = result[0]['resources'][0]['id']
    offset = 0
    while True:
        rval = lc.action.datastore_search(resource_id=resource_id,
            limit=BATCH_SIZE, offset=offset)
        records = rval['records']
        if not records:
            return
        yield records
        offset += len(records)

def _update_records(records, org_detail, conn):
    """
    """
    out = []
    org = org_detail['name']
    orghash = hashlib.md5(org).hexdigest()
    for r in records:
        unique = hashlib.md5(orghash + r['ref_number'].encode('utf-8')
            ).hexdigest()
        shortform = None
        shortform_fr = None
        for e in org_detail['extras']:
            if e['key'] == 'shortform':
                shortform = e['value']
            elif e['key'] == 'shortform_fr':
                shortform_fr = e['value']

        try:
            year, month, day = (int(x) for x in r['contract_date'].split('-'))
        except ValueError:
            print 'bad date:', r['contract_date']
            year = month = day = 0

        out.append({
            'bundle': 'proactive_disclosure',
            'id': unique,
            'ss_ref_number': r['ref_number'],
            'ss_vendor_name_en': r['vendor_name_en'],
            'ss_vendor_name_fr': r['vendor_name_fr'],
            'ss_description_code': r['description_code'],
            'ss_description_en': r['description_en'],
            'ss_description_fr': r['description_fr'],
            'ss_description_more_en': r['description_more_en'],
            'ss_description_more_fr': r['description_more_fr'],
            'ss_contract_date': r['contract_date'],
            'ss_contract_period_start': r['contract_period_start'],
            'ss_contract_period_end': r['contract_period_end'],
            'ss_delivery_date': r['delivery_date'],
            'ss_contract_value': r['contract_value'],
            'ss_original_value': r['original_value'],
            'ss_cumulative_value': r['cumulative_value'],
            'ss_comments_en': r['comments_en'],
            'ss_comments_fr': r['comments_fr'],
            'ss_additional_comments_en': r['additional_comments_en'],
            'ss_additional_comments_fr': r['additional_comments_fr'],
            'ss_org_shortform_en': shortform,
            'ss_org_shortform_fr': shortform_fr,
            'ss_org_name_en': org_detail['title'].split(' | ', 1)[0],
            'ss_org_name_fr': org_detail['title'].split(' | ', 1)[-1],
            'ss_contract_date_year': str(year),
            'ss_contract_date_month': str(month),
            'ss_contract_date_day': str(day),
            'ss_contract_date_monthname_en': calendar.month_name[month],
            'ss_contract_date_monthname_fr': MONTHS_FRA[month],
            })
    conn.add_many(out, _commit=True)
