# -*- coding: utf-8 -*-
import hashlib
import calendar
import datetime
import logging
import os
from unicodecsv import DictReader
from _csv import Error as _csvError

import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand
from solr.core import SolrException

from ckanapi import LocalCKAN, NotFound
from ckanext.recombinant.tables import (
    get_geno,
    get_chromo)
from ckanext.recombinant.read_csv import csv_data_batch
from ckanext.canada.dataset import (
    MONTHS_FR,
    solr_connection,
    data_batch,
    safe_for_solr)


TARGET_DATASET = 'ati'
WINDOW_YEARS = 2


class ATICommand(CkanCommand):
    """
    Manage the ATI Summaries SOLR index

    Usage::

        paster ati clear
                   rebuild [-f <file> <file>] [-s <solr-url>]

    Options::

        -f/--csv-file <file> <file>    use specified CSV files as ati.csv
                                       and ati-nil.csv input, instead of the
                                       (default) CKAN database
        -s/--solr-url <url>            use specified solr URL as output,
                                       instead of default from ini file.
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option(
        '-c',
        '--config',
        dest='config',
        default='development.ini',
        help='Config file to use.')
    parser.add_option(
        '-f',
        '--csv',
        nargs=2,
        dest='csv_files',
        help='CSV files to use as input (or default CKAN DB)')
    parser.add_option(
        '-s',
        '--solr-url',
        dest='solr_url',
        help='Solr URL for output')

    def command(self):
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'clear':
            return self._clear_index()
        elif cmd == 'rebuild':
            return self._rebuild(self.options.csv_files, self.options.solr_url)

    def _clear_index(self, solr_url=None, commit=True):
        conn = solr_connection('ati')
        conn.delete(q="*:*", commit=commit)

    def _rebuild(self, csv_files=None, solr_url=None):
        """
        Implement rebuild command

        :param csv_files: sequence of paths to .csv files for input
        :type csv_files: sequence of str

        :return: Nothing
        :rtype: None
        """
        self._clear_index(solr_url, False)

        conn = solr_connection('ati', solr_url)
        lc = LocalCKAN()
        if csv_files:
            for csv_file in csv_files:
                print csv_file + ':'
                firstpart, filename = os.path.split(csv_file)
                assert filename.endswith('.csv')
                resource_name = filename[:-4]

                chromo = get_chromo(resource_name)
                geno = get_geno(chromo['dataset_type'])
                assert geno.get('target_dataset') == TARGET_DATASET

                for org_id, records in csv_data_batch(csv_file, chromo):
                    records = [dict((k, safe_for_solr(v)) for k, v in
                            row_dict.items()) for row_dict in records]
                    try:
                        org_detail = lc.action.organization_show(id=org_id)
                    except NotFound:
                        continue
                    print "    {0:s} {1}".format(org_id, len(records))
                    _update_records(records, org_detail, conn)
        else:
            for org_id in lc.action.organization_list():
                count = 0
                org_detail = lc.action.organization_show(id=org_id)
                for resource_name, records in data_batch(org_detail['id'], lc, TARGET_DATASET):
                    _update_records(records, org_detail, conn)
                    count += len(records)
                print org_id, count

        print "commit"
        conn.commit()


def _update_records(records, org_detail, conn):
    """
    Update records on solr core

    :param records: record dicts
    :ptype records: sequence of record dicts

    :param org_detail: org structure as returned via local CKAN
    :ptype org_detail: dict with local CKAN org structure

    :param conn: solr connection
    :ptype conn: obj
    """
    out = []
    org = org_detail['name']
    orghash = hashlib.md5(org).hexdigest()
    today = datetime.datetime.today()
    start_year_month = (today.year - WINDOW_YEARS, today.month)
    for r in records:
        year = int(r['year'])
        month = int(r['month'])
        if (year, month) < start_year_month:
            continue
        unique = hashlib.md5(orghash
            + r.get('request_number', repr((year, month))
            ).encode('utf-8')).hexdigest()
        shortform = None
        shortform_fr = None
        ati_email = None
        month = max(1, min(12, month))
        for e in org_detail['extras']:
            if e['key'] == 'shortform':
                shortform = e['value']
            elif e['key'] == 'shortform_fr':
                shortform_fr = e['value']
            elif e['key'] == 'ati_email':
                ati_email = e['value']

        # don't ask why, just doing it the way it was done before
        en_record = {
            'bundle': 'ati_summaries',
            'hash': 'avexlb',
            'id': unique + 'en',
            'i18n_ts_en_ati_request_number': r.get('request_number', ''),
            'i18n_ts_en_ati_request_summary': r.get('summary_en', ''),
            'ss_ati_contact_information_en':
                "http://open.canada.ca/data/en/organization/about/{0}"
                .format(org),
            'ss_ati_disposition_en':
                r.get('disposition', '').split(' / ', 1)[0],
            'ss_ati_month_en': '{0:02d}'.format(month),
            'ss_ati_monthname_en': calendar.month_name[month],
            'date_clean': '%04d-%02d' % (year, month),
            'ss_ati_number_of_pages_en': r.get('pages', ''),
            'ss_ati_organization_en': org_detail['title'].split(' | ', 1)[0],
            'ss_ati_year_en': year,
            'ss_ati_org_shortform_en': shortform,
            'ss_ati_org_name_code': org,
            'ss_ati_contact_email_en': ati_email,
            'ss_ati_nothing_to_report_en': ('' if 'request_number' in r else
                'Nothing to report this month'),
            'ss_language': 'en',
            }
        fr_record = {
            'bundle': 'ati_summaries',
            'hash': 'avexlb',
            'id': unique + 'fr',
            'i18n_ts_fr_ati_request_number': r.get('request_number', ''),
            'i18n_ts_fr_ati_request_summary': r.get('summary_fr', ''),
            'ss_ati_contact_information_fr':
                "http://ouvert.canada.ca/data/fr/organization/about/{0}"
                .format(org),
            'ss_ati_disposition_fr':
                r.get('disposition', '').split(' / ', 1)[-1],
            'ss_ati_month_fr': '{0:02d}'.format(month),
            'ss_ati_monthname_fr': MONTHS_FR[month],
            'date_clean': '%04d-%02d' % (year, month),
            'ss_ati_number_of_pages_fr': r.get('pages', ''),
            'ss_ati_organization_fr': org_detail['title'].split(' | ', 1)[-1],
            'ss_ati_year_fr': year,
            'ss_ati_org_shortform_fr': shortform_fr,
            'ss_ati_org_name_code': org,
            'ss_ati_contact_email_fr': ati_email,
            'ss_ati_nothing_to_report_fr': ('' if 'request_number' in r else
                u'Rien à signaler pour cette période'),
            'ss_language': 'fr',
            }

        out.append(en_record)
        out.append(fr_record)

        record = dict(dict(en_record, **fr_record), **{
            'ss_language': 'combined',
            'id': unique,
            'organization': org_detail['title'].split(' | ', 1)[0],
            'organization_en': org_detail['title'].split(' | ', 1)[0],
            'organization_fr': org_detail['title'].split(' | ', 1)[-1],
            'year': year,
            'month': '{0:02d}'.format(month),
            'request_number': r.get('request_number', ''),
            'request_summary_en': r.get('summary_en', ''),
            'request_summary_fr': r.get('summary_fr', ''),
            'disposition': r.get('disposition', '').split(' / ', 1)[0],
            'disposition_en': r.get('disposition', '').split(' / ', 1)[0],
            'disposition_fr': r.get('disposition', '').split(' / ', 1)[-1],
            'number_of_pages': r.get('pages', ''),
            'e_mail_ati_recipient': ati_email,
            })
        out.append(record)

    try:
        conn.add(out, commit=False)
    except SolrException, e:
        print e.body
        raise
