# -*- coding: utf-8 -*-
import os
import hashlib
import calendar
import time
import logging
import json
from unicodecsv import DictReader
from _csv import Error as _csvError
from babel.numbers import format_currency

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

        if cmd == 'clear':
            return clear_index(self.command_name)
        elif cmd == 'rebuild':
            return rebuild(
                self.command_name,
                [self.options.csv_file] if self.options.csv_file else None)


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

        if cmd == 'clear':
            return clear_index(self.command_name)
        elif cmd == 'rebuild':
            return rebuild(self.command_name, self.options.csv_files)


def clear_index(command_name):
    conn = solr_connection(command_name)
    conn.delete_query("*:*")
    conn.commit()



def rebuild(command_name, csv_files=None):
    """
    Implement rebuild command

    :param csv_file: path to .csv file for input
    :type csv_file: str

    :return: Nothing
    :rtype: None
    """
    clear_index(command_name)

    conn = solr_connection(command_name)
    lc = LocalCKAN()
    if csv_files:
        for csv_file in csv_files:
            print csv_file + ':'
            unmatched = None
            for resource_name, org_id, records in csv_data_batch(csv_file, command_name):
                try:
                    org_detail = lc.action.organization_show(id=org_id)
                except NotFound:
                    continue
                print "    {0:s} {1}".format(org_id, len(records))
                unmatched = _update_records(
                    records, org_detail, conn, resource_name, unmatched)
    else:
        for org in lc.action.organization_list():
            count = 0
            org_detail = lc.action.organization_show(id=org)
            unmatched = None
            for resource_name, records in data_batch(org_detail['id'], lc, command_name):
                unmatched = _update_records(
                    records, org_detail, conn, resource_name, unmatched)
                count += len(records)
            print org, count


def _update_records(records, org_detail, conn, resource_name, unmatched):
    """
    Update records on solr core

    :param records: record dicts
    :param org_detail: org structure as returned via local CKAN
    :param conn: solr connection
    :param resource_name: type being updated
    :param unmatched: yet-unmatched values for comparing prev/next year

    :returns: new unmatched for next call for same org+resource_name
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

    if any('solr_compare_previous_year' in f for f in chromo['fields']):
        if not unmatched:
            # previous years, next years
            unmatched = ({}, {})
    else:
        unmatched = None

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

            facet_range = f.get('solr_dollar_range_facet')
            if facet_range:
                try:
                    float_value = float(value)
                except ValueError:
                    pass
                else:
                    solrrec.update(dollar_range_facet(
                        key,
                        facet_range,
                        float_value))

            sum_to = list_or_none(f.get('solr_sum_to_field'))
            if sum_to:
                for fname in sum_to:
                    sum_to_field(solrrec, fname, value)

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
            if choices:
                if key.endswith('_code'):
                    key = key[:-5]
                solrrec[key + '_en'] = recombinant_language_text(
                    choices.get(value, ''), 'en')
                solrrec[key + '_fr'] = recombinant_language_text(
                    choices.get(value, ''), 'fr')

        solrrec['text'] = u' '.join(unicode(v) for v in solrrec.values())

        if unmatched:
            match_compare_output(solrrec, out, unmatched, chromo)
        else:
            out.append(solrrec)

    if out:
        conn.add_many(out, _commit=True)
    return unmatched


def date2zulu(yyyy_mm_dd):
    return time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.mktime(time.strptime(
            '{0:s} 00:00:00'.format(yyyy_mm_dd),
            "%Y-%m-%d %H:%M:%S"))))

def list_or_none(v):
    """
    None -> None
    "str" -> ["str"]
    ["a", "b"] -> ["a", "b"]
    """
    if v is None:
        return
    # accept list or single field name from config
    if not isinstance(v, list):
        return [v]
    return v


def en_dollars(v):
    return format_currency(v, 'CAD', locale='en_CA')


def fr_dollars(v):
    return format_currency(v, 'CAD', locale='fr_CA')


def dollar_range_facet(key, facet_range, float_value):
    """
    return solr range fields for dollar float_value in ranges
    given by facet_range, in English and French

    E.g. if facet_range is: [0, 1000, 5000] then resulting facets will be
    "$0 - $999.99", "$1,000 - $4,999.99", "$5,000 +" in English
    """
    last_fac = None
    for i, fac in enumerate(facet_range):
        if float_value < fac:
            break
        last_fac = fac
    else:
        return {
            key + u'_range': unicode(i),
            key + u'_en': en_dollars(fac) + u'+',
            key + u'_fr': fr_dollars(fac) + u' +'}

    if last_fac is None:
        return {}

    return {
        key + u'_range': unicode(i - 1),
        key + u'_en': en_dollars(last_fac) + u' - ' + en_dollars(fac-0.01),
        key + u'_fr': fr_dollars(last_fac) + u' - ' + fr_dollars(fac-0.01)}


def sum_to_field(solrrec, key, value):
    """
    modify solrrec dict in-place to add this value to solrrec[key]
    """
    try:
        float_value = float(value)
    except ValueError:
        solrrec[key] = None # failed to find sum
        return
    try:
        solrrec[key] = float_value + solrrec.get(key, 0)
    except TypeError:
        pass # None can stay as None


def match_compare_output(solrrec, out, unmatched, chromo):
    """
    pop matching prev/next records from unmatched, create compare fields
    and append on out
    """
    year = int(solrrec['year'])
    prev_years, next_years = unmatched
    p_rec = prev_years.pop(year - 1, None)
    if p_rec:
        out.append(compare_output(p_rec, solrrec, chromo))
    else:
        next_years[year] = solrrec
    n_rec = next_years.pop(year + 1, None)
    if n_rec:
        out.append(compare_output(solrrec, n_rec, chromo))
    else:
        prev_years[year] = solrrec


def compare_output(prev_solrrec, solrrec, chromo):
    """
    process solr_compare_previous_year fields and return solrrec with
    extra sum and change fields added
    """
    out = dict(solrrec)

    for f in chromo['fields']:
        comp = f.get('solr_compare_previous_year')
        if not comp:
            continue
        prev_value = prev_solrrec[f['datastore_id']]
        out[comp['previous_year']] = prev_value
        try:
            float_prev = float(prev_value)
            float_cur = float(solrrec[f['datastore_id']])
            change = float_cur - float_prev
        except ValueError:
            float_prev = None
            float_cur = None
            change = None

        out[comp['change']] = change

        if 'sum_previous_year' in comp:
            for sp in list_or_none(comp['sum_previous_year']):
                sum_to_field(out, sp, float_prev)
        if 'sum_change' in comp:
            for sc in list_or_none(comp['sum_change']):
                sum_to_field(out, sc, change)

    return out
