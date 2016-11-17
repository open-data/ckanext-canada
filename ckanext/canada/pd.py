# -*- coding: utf-8 -*-
import os
import hashlib
import calendar
import time
import logging
import json
from unicodecsv import DictReader
from _csv import Error as _csvError

import paste.script
from pylons import config
from ckan.lib.cli import CkanCommand

from ckanapi import LocalCKAN, NotFound

from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.helpers import (
    recombinant_choice_fields,
    recombinant_language_text)

from ckanext.canada.dataset import (
    solr_connection,
    data_batch,
    csv_data_batch)


class PDCommand(CkanCommand):
    """
    Manage the Proactive Disclosures SOLR indexes + data files

    Usage::

        paster <pd-type> build-templates <sources> <dest-dir>
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

        elif cmd == 'clear':
            return clear_index(self.command_name)
        elif cmd == 'rebuild':
            return rebuild([self.options.csv_file])


class PDNilCommand(CkanCommand):
    """
    Manage the Proactive Disclosures SOLR indexes + data files

    Usage::

        paster <pd-type> clear
                         rebuild [-f <file> <file>]

    Options::

        -f/--csv-file <file> <file>     use specified CSV files as PD and
                                        PD-nil input, instead of the
                                        (default) CKAN database
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')
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

        elif cmd == 'clear':
            return clear_index(self.command_name)
        elif cmd == 'rebuild':
            return rebuild(self.options.csv_files)


def clear_index(self):
    conn = solr_connection(self.command_name)
    conn.delete_query("*:*")
    conn.commit()



def rebuild(self, csv_files=None):
    """
    Implement rebuild command

    :param csv_file: path to .csv file for input
    :type csv_file: str

    :return: Nothing
    :rtype: None
    """
    self._clear_index()

    conn = solr_connection(self.command_name)
    lc = LocalCKAN()
    if csv_files:
        for csv_file in csv_files:
            print csv_file + ':'
            for resource_name, org_id, records in csv_data_batch(csv_file, self.command_name):
                try:
                    org_detail = lc.action.organization_show(id=org_id)
                except NotFound:
                    continue
                print "    {0:s} {1}".format(org_id, len(records))
                _update_records(records, org_detail, conn, resource_name)
    else:
        for org in lc.action.organization_list():
            count = 0
            org_detail = lc.action.organization_show(id=org)
            for resource_name, records in data_batch(org_detail['id'], lc, self.command_name):
                _update_records(records, org_detail, conn, resource_name)
                count += len(records)
            print org, count


def _update_records(records, org_detail, conn, resource_name):
    """
    Update records on solr core

    :param records: record dicts
    :ptype records: sequence of record dicts

    :param org_detail: org structure as returned via local CKAN
    :ptype org_detail: dict with local CKAN org structure

    :param conn: solr connection
    :ptype conn: obj

    :param resource_name: type being updated
    """
    chromo = get_chromo(resource_name)
    pk = chromo.get('datastore_primary_key', [])
    if not isinstance(pk, list):
        pk = [pk]

    org = org_detail['name']
    orghash = hashlib.md5(org).hexdigest()

    def unique_id(r):
        "return hash, friendly id"
        s = orghash
        f = org
        if not pk:
            s = hashlib.md5(s + recombinant_type + "-%d" % r['_id']).hexdigest()
            f += u'|' + unicode(r['_id'])
        for k in pk:
            s = hashlib.md5(s + r[k].encode('utf-8')).hexdigest()
            f += u'|' + unicode(r[k])
        return s, f

    out = []

    choice_fields = dict(
        (f['datastore_id'], dict(f['choices']))
        for f in recombinant_choice_fields(resource_name, all_languages=True))

    for r in records:
        unique, friendly = unique_id(r)

        shortform = None
        shortform_fr = None
        for e in org_detail['extras']:
            if e['key'] == 'shortform':
                shortform = e['value']
            elif e['key'] == 'shortform_fr':
                shortform_fr = e['value']

        solrrec = {
            'id': unique,
            'unique_id': friendly,
            'org_name_code': org_detail['name'],
            'org_name_en': org_detail['title'].split(' | ', 1)[0],
            'org_name_fr': org_detail['title'].split(' | ', 1)[-1],
            }

        for f in chromo['fields']:
            key = f['datastore_id']
            value = r[key]

            facet_range = f.get('solr_float_range_facet')
            if facet_range:
                try:
                    float_value = float(value)
                except ValueError:
                    pass
                else:
                    for i, fac in enumerate(facet_range):
                        if 'less_than' not in fac or float_value < fac['less_than']:
                            solrrec[key + '_range'] = str(i)
                            solrrec[key + '_range_en'] = fac['label'].split(' | ')[0]
                            solrrec[key + '_range_fr'] = fac['label'].split(' | ')[-1]
                            break

            if f.get('datastore_type') == 'date':
                try:
                    value = date2zulu(value)
                    # CM: If this only applies to PD types this should be accurate
                    # CM: This should only apply if valid (as per date2zulu) else NULL
                    if f.get('extract_date_year'):
                        solrrec['date_year'] = value.split('-', 1)[0]
                    if f.get('extract_date_month'):
                        solrrec['date_month'] = value.split('-')[1]
                except ValueError:
                    pass
            solrrec[key] = value

            choices = choice_fields.get(f['datastore_id'])
            if not choices:
                continue

            if key.endswith('_code'):
                key = key[:-5]
            solrrec[key + '_en'] = recombinant_language_text(
                choices.get(value, ''), 'en')
            solrrec[key + '_fr'] = recombinant_language_text(
                choices.get(value, ''), 'fr')

        solrrec['text'] = u' '.join(unicode(v) for v in solrrec.values())
        out.append(solrrec)

    conn.add_many(out, _commit=True)


def date2zulu(yyyy_mm_dd):
    return time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.mktime(time.strptime(
            '{0:s} 00:00:00'.format(yyyy_mm_dd),
            "%Y-%m-%d %H:%M:%S"))))
