import click
import os
import hashlib
import calendar
import time
from babel.numbers import format_currency, format_decimal

from ckanapi import LocalCKAN, NotFound

from ckanext.recombinant.tables import (
    get_geno,
    get_chromo,
    get_dataset_types)
from ckanext.recombinant.errors import RecombinantException
from ckanext.recombinant.read_csv import csv_data_batch
from ckanext.recombinant.helpers import (
    recombinant_choice_fields,
    recombinant_language_text)

from ckanext.canada.dataset import (
    MONTHS_FR,
    solr_connection,
    data_batch,
    safe_for_solr)

SOLR_MAX_UTF8_LENGTH = 28000


def get_commands():
    return pd


def _check_pd_type(pd_type):
    if pd_type not in get_dataset_types():
        raise RecombinantException(f'PD Type "{pd_type}" does not exist')


@click.group(short_help="Proactive Disclosure/Publication management commands")
def pd():
    """Proactive Disclosure/Publication management commands.
    """
    pass


@pd.command(short_help="List the available PD types.")
def list_types():
    for pd_type in get_dataset_types():
        click.echo(pd_type)


@pd.command(short_help="Clear all SOLR records.")
@click.argument("pd_type")
def clear(pd_type):
    _check_pd_type(pd_type)
    clear_index(pd_type)


@pd.command(short_help="Rebuilds and reindexes all SOLR records.")
@click.argument("pd_type")
@click.option(
    "--lenient",
    is_flag=True,
    help="Allow rebuild from csv files without checking hat columns match expected columns.",
)
@click.option(
    "-f",
    "--files",
    default=None,
    multiple=True,
    help="CSV file(s) to use as input (or default CKAN DB). Use PD and PD-nil files for NIL types.",
)
@click.option(
    "-s",
    "--solr-url",
    default=None,
    help="Solr URL for output.",
)
@click.option(
    "-n",
    "--has-nil",
     is_flag=True,
    help="If the PD Type is a NIL type.",
)
def rebuild(pd_type, files=None, solr_url=None, lenient=False, has_nil=False):
    """
    Rebuilds and reindexes all SOLR records.

    Full Usage:\n
        pd <pd-type> rebuild [--lenient] [-f <file>] [-s <solr-url>]

    For NIL:\n
        pd <pd-type> rebuild [--lenient] [-f <file> <file>] [-s <solr-url>]
    """
    _check_pd_type(pd_type)
    if files:
        if not has_nil and len(files) >= 2:
            raise ValueError('You may only supply one file for non NIL types')
        if len(files) > 2:
            raise ValueError('You may only supply up to two files')
    strict = True
    if lenient:
        strict = False
    rebuild(pd_type,
            files,
            solr_url,
            strict)


def clear_index(pd_type, solr_url=None, commit=True):
    conn = solr_connection(pd_type, solr_url)
    conn.delete(q="*:*", commit=commit)


def rebuild(pd_type, csv_files=None, solr_url=None, strict=True):
    """
    Implement rebuild command

    :param csv_file: path to .csv file for input
    :type csv_file: str

    :return: Nothing
    :rtype: None
    """
    clear_index(pd_type, solr_url, False)

    conn = solr_connection(pd_type, solr_url)
    lc = LocalCKAN()
    if csv_files:
        for csv_file in csv_files:
            print(csv_file + ':')
            prev_org = None
            unmatched = None
            firstpart, filename = os.path.split(csv_file)
            assert filename.endswith('.csv')
            resource_name = filename[:-4]

            chromo = get_chromo(resource_name)
            geno = get_geno(chromo['dataset_type'])

            for org_id, records in csv_data_batch(csv_file, chromo, strict=strict):
                records = [dict((k, safe_for_solr(v)) for k, v in
                            row_dict.items()) for row_dict in records]
                if org_id != prev_org:
                    unmatched = None
                try:
                    org_detail = lc.action.organization_show(id=org_id)
                except NotFound:
                    continue
                print("    {0:s} {1}".format(org_id, len(records)))
                unmatched = _update_records(
                    records, org_detail, conn, resource_name, unmatched)
    else:
        for org in lc.action.organization_list():
            count = 0
            org_detail = lc.action.organization_show(id=org)
            unmatched = None
            for resource_name, records in data_batch(org_detail['id'], lc, pd_type):
                unmatched = _update_records(
                    records, org_detail, conn, resource_name, unmatched)
                count += len(records)
            print(org, count)

    print("commit")
    conn.commit()


def _update_records(records, org_detail, conn, resource_name, unmatched, retry=True):
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
    orghash = hashlib.md5(org.encode('utf-8')).hexdigest()

    def unique_id(r):
        "return hash, friendly id, partial id"
        s = orghash
        f = org
        p = org
        for k in pk:
            s = hashlib.md5((s + r[k]).encode('utf-8')).hexdigest()
            f += u'|' + str(r[k])
            if u'|' not in p:
                p += u'|' + str(r[k])
        return s, f, p

    out = []

    choice_fields = recombinant_choice_fields(resource_name, all_languages=True)

    if any('solr_compare_previous_year' in f for f in chromo['fields']):
        if not unmatched:
            # previous years, next years
            unmatched = ({}, {})
    else:
        unmatched = None

    # track failed choice fields for debugging
    # and cleaning up old data.
    failed_choices = {}

    def _record_failed_choice(_key, _value):
        if _key not in failed_choices:
            failed_choices[_key] = {}
        if _value not in failed_choices[_key]:
            failed_choices[_key][_value] = 1
        else:
            failed_choices[_key][_value] += 1

    for r in records:
        unique, friendly, partial = unique_id(r)
        if chromo.get('solr_legacy_ati_ids', False):
            # for compatibility with existing urls
            unique = hashlib.md5((orghash
                + r.get('request_number', repr((int(r['year']), int(r['month'])))
                )).encode('utf-8')).hexdigest()

        solrrec = {
            'id': unique,
            'unique_id': friendly,
            'partial_id': partial,
            'org_name_code': org_detail['name'],
            'org_name_en': org_detail['title_translated']['en'],
            'org_name_fr': org_detail['title_translated']['fr'],
            }

        org_fields = chromo.get('solr_org_fields')
        if org_fields:
            for e in org_fields:
                if e in org_detail:
                    solrrec[e] = org_detail[e]

        for f in chromo['fields']:
            key = f['datastore_id']
            value = r.get(key, '')

            facet_range = f.get('solr_dollar_range_facet')
            if facet_range:
                try:
                    float_value = float(value.replace('$','').replace(',',''))
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
                    if f.get('extract_date_clean'):
                        solrrec['date_clean'] = value
                except ValueError:
                    pass
            elif f.get('extract_date_year'):
                if f.get('datastore_type') == 'year':
                    solrrec['date_year'] = value
                else:
                    try:
                        solrrec['date_year'] = int(value.split('-', 1)[0])
                    except ValueError:
                        pass
            if f.get('extract_double_sortable'):
                try:
                    solrrec['doubl_' + key] = float(value)
                except ValueError:
                    pass

            # limit text values to 28kB for indexing. Solr max 32kB minus a threshold for synonym replacements.
            solrrec[key] = value.encode('utf-8')[:SOLR_MAX_UTF8_LENGTH].decode() if (f.get('datastore_type') == 'text' and len(value.encode('utf-8')) > SOLR_MAX_UTF8_LENGTH) else value

            choices = choice_fields.get(f['datastore_id'])
            if choices:
                if key.endswith('_code'):
                    key = key[:-5]
                if f.get('datastore_type') == '_text':
                    # special handling for _text types, joining the multiple choices with semicolons (;)
                    english_choices = []
                    french_choices = []
                    for v in value.split(','):
                        choice = dict(choices).get(v)
                        if (not choice and v) or (not v and (f.get('form_required') or f.get('excel_required'))):
                            # not a valid choice, or empty value on a required field
                            _record_failed_choice(key, v)
                        if choice:
                            english_choices.append(recombinant_language_text(choice, 'en'))
                            french_choices.append(recombinant_language_text(choice, 'fr'))
                    solrrec[key + '_en'] = '; '.join(english_choices)
                    solrrec[key + '_fr'] = '; '.join(french_choices)
                else:
                    choice = dict(choices).get(value, {})
                    if (not choice and value) or (not value and (f.get('form_required') or f.get('excel_required'))):
                        # not a valid choice, or empty value on a required field
                        _record_failed_choice(key, value)
                    _add_choice(solrrec, key, r, choice, f)

            if f.get('solr_month_names', False):
                solrrec[key] = str(value).zfill(2)
                solrrec[key + '_name_en'] = calendar.month_name[int(value)]
                solrrec[key + '_name_fr'] = MONTHS_FR[int(value)]

        solrrec['text'] = u' '.join(str(v) for v in solrrec.values())

        if 'solr_static_fields' in chromo:
            solrrec.update(chromo['solr_static_fields'])

        ssrf = chromo.get('solr_sum_range_facet')
        if ssrf:
            key = ssrf['sum_field']
            float_value = float(solrrec[key])
            solrrec.update(numeric_range_facet(
                key,
                ssrf['facet_values'],
                float_value))

        if unmatched:
            match_compare_output(solrrec, out, unmatched, chromo)
        else:
            out.append(solrrec)

    if failed_choices:
        for _key, _values in failed_choices.items():
            for _value, _count in _values.items():
                print("    %s -- WARNING: '%s' invalid option '%s' (%s)" % (org_detail['name'],
                                                                            _key,
                                                                            _value,
                                                                            _count))

    if unmatched:
        out.extend(unmatched[1].values())

    import pysolr
    for a in reversed(range(10)):
        try:
            if out:
                conn.add(out, commit=False)
            break
        except pysolr.SolrError:
            if not a or not retry:
                raise
            print("waiting...")
            import time
            time.sleep((10-a) * 5)
            print("retrying...")
    return unmatched


def _add_choice(solrrec, key, record, choice, field):
    """
    add the english+french values for choice to solrrec
    """
    solrrec[key + '_en'] = recombinant_language_text(choice, 'en')
    solrrec[key + '_fr'] = recombinant_language_text(choice, 'fr')

    # lookups used for choices that expand to multiple values
    if 'lookup' in choice:
        lookup = choice['lookup']
    elif 'conditional_lookup' in choice:
        for conditional in choice['conditional_lookup']:
            if 'column' in conditional:
                column = record[conditional['column']]
                if not column < conditional['less_than']:
                    continue
            lookup = conditional['lookup']
            break
    else:
        return
    solrrec['multi_' + key + '_en'] = [
        recombinant_language_text(field['choices_lookup'][cl], 'en')
        for cl in lookup]
    solrrec['multi_' + key + '_fr'] = [
        recombinant_language_text(field['choices_lookup'][cl], 'fr')
        for cl in lookup]


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
        "A: $5,000 +"
        "B: $1,000 - $4,999.99"
        "C: $0 - $999.99"
    in English
    """
    last_fac = None
    for i, fac in enumerate(facet_range):
        if float_value < fac:
            break
        last_fac = fac
    else:
        return {
            key + u'_range': str(i),
            key + u'_en': u'A: ' + en_dollars(fac) + u'+',
            key + u'_fr': u'A: ' + fr_dollars(fac) + u' +'}

    if last_fac is None:
        return {}

    prefix = chr(ord('A') + len(facet_range) - i) + u': '
    return {
        key + u'_range': str(i - 1),
        key + u'_en': prefix + en_dollars(last_fac) + u' - ' + en_dollars(fac-0.01),
        key + u'_fr': prefix + fr_dollars(last_fac) + u' - ' + fr_dollars(fac-0.01)}


def en_numeric(v):
    return format_decimal(v, locale='en_CA')


def fr_numeric(v):
    return format_decimal(v, locale='fr_CA')


def numeric_range_facet(key, facet_range, float_value):
    """
    return solr range fields for numeric float_value in ranges
    given by facet_range, in English and French

    E.g. if facet_range is: [0, 1000, 5000] then resulting facets will be
        "A: 5,000"
        "B: 1,000 - 4,999"
        "C: 0 - 999"
    in English
    """
    last_fac = None
    for i, fac in enumerate(facet_range):
        if float_value < fac:
            break
        last_fac = fac
    else:
        return {
            key + u'_range': str(i),
            key + u'_en': u'A: ' + en_numeric(fac) + u'+',
            key + u'_fr': u'A: ' + fr_numeric(fac) + u' +'}

    if last_fac is None:
        return {}

    prefix = chr(ord('A') + len(facet_range) - i) + u': '
    return {
        key + u'_range': str(i - 1),
        key + u'_en': prefix + en_numeric(last_fac) + u' - ' + en_numeric(fac-1),
        key + u'_fr': prefix + fr_numeric(last_fac) + u' - ' + fr_numeric(fac-1)}


def sum_to_field(solrrec, key, value):
    """
    modify solrrec dict in-place to add this value to solrrec[key]
    """
    try:
        if isinstance(value, str):
            float_value = float(value.replace(',', ''))
        else:
            float_value = float(value)
    except (ValueError, TypeError):
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
        except ValueError:
            float_prev = None
        try:
            float_cur = float(solrrec[f['datastore_id']])
        except ValueError:
            float_cur = None
        if float_prev is not None and float_cur is not None:
            change = float_cur - float_prev
        else:
            change = None

        out[comp['change']] = change

        if 'sum_previous_year' in comp:
            for sp in list_or_none(comp['sum_previous_year']):
                sum_to_field(out, sp, float_prev)
        if 'sum_change' in comp:
            sum_change = (float_cur or 0) - (float_prev or 0)
            for sc in list_or_none(comp['sum_change']):
                sum_to_field(out, sc, sum_change)

    return out
