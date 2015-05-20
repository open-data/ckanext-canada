#!/usr/bin/env python

"""
Transform metadata .jsonl file from CKAN 2.1 alignment to 2.3
    Usage::
    python meta_xform.py <input file> <output file>
"""

from os import readlink

import gzip
import logging
import os.path as path
import subprocess
import sys

# from pylons.i18n import _
import simplejson

SUFFIX_FRA = '_fra'
LEN_SUFFIX_FRA = len(SUFFIX_FRA)
LANG_KEYS = ('en', 'fr')
SP_SP = '  '
SP_PIPE_SP = ' | '

# new schema description, data field choices
sd_new = None
sd_new_dfc = None

def _is_geodata(rec):
    """
    Return True if the input record contains Geo Data, False otherwise
    """
    return (('catalog_type' in rec) and
        isinstance(rec['catalog_type'], unicode) and
        not rec['catalog_type'].startswith(u'Geo '))

def _process(line):
    """
    Process one JSONL record of input, return None if Geo data and
    metadata in alignment with ckan-2.3 otherwise
    """
    rec = simplejson.loads(line)

    # filter out Geo data
    if not _is_geodata(rec):
        _process.count[0] += 1
        logging.debug('Skipped {0}, processed {1}'.format(*_process.count))
        return None

    logging.debug('Before:')
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))

    # replace dataset type
    rec['type'] = u'dataset'

    # dump tags: redundant
    rec['tags'] = []

    # merge biligual keys -- only keywords ought to become a list
    bi_fr_keys = [k for k in rec.keys() if k.endswith(SUFFIX_FRA)]
    for k_fra in bi_fr_keys:
        k = k_fra[:-LEN_SUFFIX_FRA]
        if k == 'keywords':
            rec[k] = dict(zip(LANG_KEYS, (
                [] if rec.get(k) is None else [
                    token.strip() for token in rec.pop(k).split(',')],
                [] if rec.get(k_fra) is None else [
                    token.strip() for token in rec.pop(k_fra).split(',')])))
        else:
            rec[k] = dict(zip(LANG_KEYS, (
                rec.pop(k, None),
                rec.pop(k_fra, None))))

    # convert subject english-sp-sp-french content to fluent text
    rec['subject'] = [
        sd_new_dfc['subject'][s.lstrip().split(SP_SP, 1)[0]]
            for s in rec['subject']]

    # convert frenquency english-sp-pipe-sp-french content to fluent text
    freq = rec.pop('maintenance_and_update_frequency')
    if (freq):
        rec['frequency'] = sd_new_dfc[u'frequency'][
            freq.lstrip().split(SP_PIPE_SP, 1)[0]]

    # convert geo region english-sp-sp-french content to fluent text
    rec['geographic_region'] = [
        sd_new_dfc[u'geographic_region'][gr.lstrip().split(SP_SP, 1)[0]]
            for gr in rec['geographic_region']]

    # merge per-resource name, name_fra to fluent text
    for r in rec['resources']:
        r['name'] = dict(
            zip(LANG_KEYS, (r.pop('name', None), r.pop('name_fra', None))))

    _process.count[1] += 1
    logging.debug('Skipped {0}, processed {1}'.format(*_process.count))
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))
    return rec
_process.count = [0, 0]

def _main(fpath_jsonl_old, fpath_jsonl_new):
    """
    With input JSONL data file, open and process a line at a time;
    write output to gzipped JSONL new-style file
    """
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    with gzip.open(fpath_jsonl_old, 'rb') as fp_in:
        with gzip.open(fpath_jsonl_new, 'wb') as fp_out:
            try:
                for line in fp_in:
                    rec = _process(line.rstrip())
                    if (rec):
                        fp_out.write(simplejson.dumps(rec) + '\n')
            except IOError:
                print >> sys.stderr, (
                    'Error: input file <{0}> not gzipped'.format(
                        fpath_jsonl_old))

def usage():
    """
    Display usage message
    """
    print >> sys.stderr, (
        'Usage: python {0} <in-file> <out-file>'.format(sys.argv[0]))
    print >> sys.stderr, (
        'where <in-file> is a gzipped ckanext-canada@v2.1 metadata file')
    print >> sys.stderr, (
        'and <out-file> will be a gzipped ckanext-canada@v2.3 metadata file.')
    sys.exit(-1)

def _set_new_schema_dataset_choices():
    """
    Initialize tree of choices (label:value) for new schema dataset
    choice fields
    """
    global sd_new_dfc
    _HERE = path.dirname(path.abspath(__file__))
    _SCHEMAS_DIR = path.join(path.dirname(_HERE),'ckanext/canada/schemas')
    _JSON_NAME = path.join(_SCHEMAS_DIR, 'raw.json')

    with open(_JSON_NAME) as j:
        sd_new = simplejson.load(j)
    sd_new_dfc = dict((
        df['field_name'],
        dict((
            ch['label']['en'].replace(',', ''),
            ch['value']) for ch in df['choices']))
        for df in sd_new['dataset_fields'] if 'choices' in df)

if __name__ == '__main__':
    """
    Main line: check arguments, init global schema variable,  and dispatch
    """
    fpath_jsonl_old = None
    fpath_jsonl_new = None

    # Need at least two args: input and output paths
    if len(sys.argv) < 3:
        usage()

    # Input path must refer to a regular file or a sym-link to a regular file
    fpath_jsonl_old = sys.argv[1]
    if path.islink(fpath_jsonl_old):
        fpath_jsonl_old = readlink(fpath_jsonl_old)
    if not path.isfile(fpath_jsonl_old):
        usage()

    # Input path must refer to a gzipped file
    fpath_jsonl_old = path.expanduser(
        path.expandvars(path.abspath(fpath_jsonl_old)))

    fpath_jsonl_new = path.expanduser(
        path.expandvars(path.abspath(sys.argv[2])))

    # Set dataset choice tree
    _set_new_schema_dataset_choices()

    # Process input file
    _main(fpath_jsonl_old, fpath_jsonl_new)
