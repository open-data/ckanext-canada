# -*- coding: utf-8 -*-
import hashlib
import calendar
import datetime
import logging
from unicodecsv import DictReader
from _csv import Error as _csvError

import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand

from ckanapi import LocalCKAN

from ckanext.canada.dataset import (
    MONTHS_FR,
    solr_connection,
    data_batch,
    csv_data_batch)


TARGET_DATASET = 'ati'
WINDOW_YEARS = 2


class ATICommand(CkanCommand):
    """
    Manage the ATI Summaries SOLR index

    Usage::

        paster ati clear
                   rebuild [-f <file> <file>]

    Options::

        -f/--csv-file <file> <file>    use specified CSV files as ati-summaries
                                       and ati-none input, instead of the
                                       (default) CKAN database
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

    def command(self):
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        if cmd == 'clear':
            return self._clear_index()
        elif cmd == 'rebuild':
            return self._rebuild(self.options.csv_files)

    def _clear_index(self):
        conn = solr_connection('ati_summaries')
        conn.delete_query("*:*")
        conn.commit()

    def _rebuild(self, csv_files=None):
        """
        Implement rebuild command

        :param csv_files: sequence of paths to .csv files for input
        :type csv_files: sequence of str

        :return: Nothing
        :rtype: None
        """

        conn = solr_connection('ati_summaries')
        lc = LocalCKAN()
        if csv_files:
            count = {}
            for csv_file in csv_files:
                print csv_file + ':'
                count[csv_file] = {}
                for org_recs in csv_data_batch(csv_file, TARGET_DATASET):
                    org_id = org_recs.keys()[0]
                    if org_id not in count[csv_file]:
                        count[csv_file][org_id] = 0
                    org_detail = lc.action.organization_show(id=org_id)
                    records = org_recs[org_id]
                    _update_records(records, org_detail, conn)
                    count[csv_file][org_id] += len(records)
                for k, v in count[csv_file].iteritems():
                    print "    {0:s} {1}".format(k, v)
            for org_id in lc.action.organization_list():
                print org_id, sum((count[f].get(org_id, 0) for f in count))
        else:
            for org_id in lc.action.organization_list():
                count = 0
                org_detail = lc.action.organization_show(id=org_id)
                for records in data_batch(org_detail['id'], lc, TARGET_DATASET):
                    _update_records(records, org_detail, conn)
                    count += len(records)
                print org_id, count
            #rval = conn.query("*:*" , rows=2)


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
    today = datetime.datetime.today()
    start_year_month = (today.year - WINDOW_YEARS, today.month)
    for r in records:
        if (r['year'], r['month']) < start_year_month:
            continue
        unique = hashlib.md5(orghash
            + r.get('request_number', repr((r['year'], r['month']))
            ).encode('utf-8')).hexdigest()
        shortform = None
        shortform_fr = None
        ati_email = None
        month = max(1, min(12, r['month']))
        for e in org_detail['extras']:
            if e['key'] == 'shortform':
                shortform = e['value']
            elif e['key'] == 'shortform_fr':
                shortform_fr = e['value']
            elif e['key'] == 'ati_email':
                ati_email = e['value']

        # don't ask why, just doing it the way it was done before
        out.append({
            'bundle': 'ati_summaries',
            'hash': 'avexlb',
            'id': unique + 'en',
            'i18n_ts_en_ati_request_number': r.get('request_number', ''),
            'i18n_ts_en_ati_request_summary': r.get('summary_eng', ''),
            'ss_ati_contact_information_en':
                "http://data.gc.ca/data/en/organization/about/{0}"
                .format(org),
            'ss_ati_disposition_en':
                r.get('disposition', '').split(' / ', 1)[0],
            'ss_ati_month_en': '{0:02d}'.format(int(r['month'])),
            'ss_ati_monthname_en': calendar.month_name[month],
            'ss_ati_number_of_pages_en': r.get('pages', ''),
            'ss_ati_organization_en': org_detail['title'].split(' | ', 1)[0],
            'ss_ati_year_en': r['year'],
            'ss_ati_org_shortform_en': shortform,
            'ss_ati_contact_email_en': ati_email,
            'ss_ati_nothing_to_report_en': ('' if 'request_number' in r else
                'Nothing to report this month'),
            'ss_language': 'en',
            })
        out.append({
            'bundle': 'ati_summaries',
            'hash': 'avexlb',
            'id': unique + 'fr',
            'i18n_ts_fr_ati_request_number': r.get('request_number', ''),
            'i18n_ts_fr_ati_request_summary': r.get('summary_fra', ''),
            'ss_ati_contact_information_fr':
                "http://donnees.gc.ca/data/fr/organization/about/{0}"
                .format(org),
            'ss_ati_disposition_fr':
                r.get('disposition', '').split(' / ', 1)[-1],
            'ss_ati_month_fr': '{0:02d}'.format(int(r['month'])),
            'ss_ati_monthname_fr': MONTHS_FR[month],
            'ss_ati_number_of_pages_fr': r.get('pages', ''),
            'ss_ati_organization_fr': org_detail['title'].split(' | ', 1)[-1],
            'ss_ati_year_fr': r['year'],
            'ss_ati_org_shortform_fr': shortform_fr,
            'ss_ati_contact_email_fr': ati_email,
            'ss_ati_nothing_to_report_fr': ('' if 'request_number' in r else
                u'Rien à signaler ce mois-ci'),
            'ss_language': 'fr',
            })
    conn.add_many(out, _commit=True)
