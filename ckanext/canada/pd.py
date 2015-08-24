# -*- coding: utf-8 -*-
import os
import hashlib
import calendar
import time
import logging
from unicodecsv import DictReader
from _csv import Error as _csvError

import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand

from ckanapi import LocalCKAN, NotFound

from ckanext.recombinant.write_xls import xls_template
from ckanext.recombinant.plugins import get_table, get_dataset_types

from ckanext.canada.dataset import (
    MONTHS_FR,
    solr_connection,
    data_batch,
    csv_data_batch)


TARGET_DATASET = 'pd'
SPLIT_XLS_ROWS = 50002


class PDCommand(CkanCommand):
    """
    Manage the Proactive Disclosures SOLR indexes + data files

    Usage::

        paster contracts build-templates <sources> <dest-dir>
                         clear
                         rebuild [-f <file>]

    Options::

        -f/--csv-file <file>       use specified CSV files as contracts input,
                                   instead of the (default) CKAN database
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
    parser.add_option(
        '-f',
        '--csv',
        dest='csv_file',
        help='CSV file to use as input (or default CKAN DB)')

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
            return self._rebuild(self.options.csv_file)

    def _clear_index(self):
        conn = solr_connection(self.command_name)
        conn.delete_query("*:*")
        conn.commit()

    def _rebuild(self, csv_file=None):
        """
        Implement rebuild command

        :param csv_file: path to .csv file for input
        :type csv_file: str

        :return: Nothing
        :rtype: None
        """
        conn = solr_connection(self.command_name)
        lc = LocalCKAN()
        if csv_file:
            count = {}
            for org_recs in csv_data_batch(csv_file, TARGET_DATASET):
                org_id = org_recs.keys()[0]
                if org_id not in count:
                    count[org_id] = 0
                org_detail = lc.action.organization_show(id=org_id)
                records = org_recs[org_id]
                _update_records(records, org_detail, conn)
                count[org_id] += len(records)
            for org_id in lc.action.organization_list():
                print org_id, count.get(org_id, 0)
        else:
            for org in lc.action.organization_list():
                count = 0
                org_detail = lc.action.organization_show(id=org)
                for records in data_batch(org_detail['id'], lc, TARGET_DATASET):
                    _update_records(records, org_detail, conn)
                    count += len(records)
                print org, count

    def _build_templates(self):
        """
        Implement build-templates command
        """
        lc = LocalCKAN()
        output_files = {}
        next_row = {}
        output_counter = {}
        output_path = self.args[2:][-1]
        dataset_types = get_dataset_types(TARGET_DATASET)
        table = get_table(dataset_types[0])

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
                org = lc.action.organization_show(
                    id=org_id, include_data_batch=False)
            except NotFound:
                logging.error('org id', org_id, 'not found')
                output_files[org_id] = None
                next_row[org_id] = 0
                return None, None
            book = xls_template(dataset_types[0], org)
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


def _update_records(records, org_detail, conn):
    """
    Update records on solr core

    :param records: record dicts
    :ptype records: sequence of record dicts

    :param org_detail: org structure as returned via local CKAN
    :ptype org_detail: dict with local CKAN org structure

    :param conn: solr connection
    :ptype conn: obj

    :returns: Nothing
    :rtype: None
    """
    out = []
    org = org_detail['name']
    orghash = hashlib.md5(org).hexdigest()
    # site_id = config.get('ckan.site_id')
    for r in records:
        unique = hashlib.md5(
            orghash + r['ref_number'].encode('utf-8')).hexdigest()
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
            logging.error('bad date:', r['contract_date'])
            year = month = day = 0

        out.append({
            'bundle': 'proactive_disclosure',
            # 'site_id': site_id,
            'id': unique,
            'ss_ref_number': r['ref_number'],
            'ss_vendor_name_en': r['vendor_name_en'],
            'ss_vendor_name_fr': r['vendor_name_fr'],
            'ss_description_code': r['description_code'],
            'ss_description_en': r['description_en'],
            'ss_description_fr': r['description_fr'],
            'ss_description_more_en': r['description_more_en'],
            'ss_description_more_fr': r['description_more_fr'],
            'ss_contract_date': date2zulu(r['contract_date']),
            'ss_contract_period_start': date2zulu(r['contract_period_start']),
            'ss_contract_period_end': date2zulu(r['contract_period_end']),
            'ss_delivery_date': date2zulu(r['delivery_date']),
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
            'ss_contract_date_monthname_fr': MONTHS_FR[month],
            })
    conn.add_many(out, _commit=True)


def date2zulu(yyyy_mm_dd):
    return time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.mktime(time.strptime(
            '{0:s} 00:00:00'.format(yyyy_mm_dd),
            "%Y-%m-%d %H:%M:%S"))))
