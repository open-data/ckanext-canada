"""
Transform metadata .jsonl file from CKAN 2.1 alignment to 2.3
"""

from os import readlink

import gzip
import logging
import os.path as path
import subprocess
import sys

# from pylons.i18n import _
import simplejson

from ckanapi import LocalCKAN

SUFFIX_FRA = '_fra'
LEN_SUFFIX_FRA = len(SUFFIX_FRA)
LANG_KEYS = ('en', 'fr')
SP_SP = '  '
SP_PIPE_SP = ' | '

# new schema description, data field choices
dataset_choices = {}
resource_choices = {}

def _process(line):
    """
    Process one JSONL record of input, return None if Geo data and
    metadata in alignment with ckan-2.3 otherwise
    """
    rec = simplejson.loads(line)

    logging.debug('Before:')
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))

    if rec.get('catalog_type','').startswith('Geo'):
        return

    if rec['type'] not in ('info', 'dataset'):
        return

    rec['collection'] = u'publication' if rec['type'] == 'info' else u'primary'
    rec['jurisdiction'] = u'federal'
    rec['restrictions'] = u'unrestricted'
    rec['imso_approval'] = u'true' if rec.get('portal_release_date') else u'false'

    # dump tags: redundant
    rec['tags'] = []

    # merge biligual keys -- only keywords ought to become a list
    bi_fr_keys = [k for k in rec.keys() if k.endswith(SUFFIX_FRA)]
    for k_fra in bi_fr_keys:
        k = k_fra[:-LEN_SUFFIX_FRA]
        if k == 'keywords':
            rec[k] = dict(zip(LANG_KEYS, (
                [] if rec.get(k) is None else [
                    token.strip() for token in rec.pop(k).split(',')
                    if token.strip()],
                [] if rec.get(k_fra) is None else [
                    token.strip() for token in rec.pop(k_fra).split(',')
                    if token.strip()])))
        else:
            rec[k] = dict(zip(LANG_KEYS, (
                rec.pop(k, None),
                rec.pop(k_fra, None))))

    # convert subject english-sp-sp-french content to fluent text
    rec['subject'] = [
        dataset_choices['subject'][s.lstrip().split(SP_SP, 1)[0]]
            for s in rec.get('subject', [])]

    rec['topic_category'] = [
        dataset_choices['topic_category'][s.lstrip().split(SP_SP, 1)[0]]
            for s in rec.get('topic_category',[])]

    if rec.get('presentation_form'):
        rec['presentation_form'] = (
            dataset_choices['presentation_form'][
                rec['presentation_form'].lstrip().split(SP_PIPE_SP, 1)[0]])

    # convert frenquency english-sp-pipe-sp-french content to fluent text
    freq = rec.pop('maintenance_and_update_frequency', rec.get('frequency'))
    if freq:
        rec['frequency'] = dataset_choices[u'frequency'].get(
            freq.lstrip().split(SP_PIPE_SP, 1)[0], freq)

    # convert geo region english-sp-sp-french content to fluent text
    rec['geographic_region'] = [
        dataset_choices[u'geographic_region'].get(
            gr.lstrip().split(SP_SP, 1)[0], gr)
        for gr in rec.get('geographic_region',[])]

    if rec.get('spatial_representation_type'):
        rec['spatial_representation_type'] = [
            dataset_choices['spatial_representation_type'][
                rec['spatial_representation_type'].lstrip().split(
                    SP_PIPE_SP, 1)[0]]]
    else:
        rec['spatial_representation_type'] = []

    if not rec.get('maintainer_email'):
        rec['maintainer_email'] = 'open-ouvert@tbs-sct.g.ca'

    rec['ready_to_publish'] = str(rec.get('ready_to_publish', 'false')).lower()

    rec['title_translated'] = rec.pop('title')
    rec['notes_translated'] = rec.pop('notes')

    rec.pop('extras', None)

    # merge per-resource name, name_fra to fluent text
    for r in rec['resources']:
        if 'name_fra' in r:
            r['name_translated'] = dict(
                zip(LANG_KEYS, (r.pop('name', None), r.pop('name_fra', None))))
        elif 'name_translaged' not in r:
            r['name_translated'] = r.pop('name')

        langs = []
        language = r.get('language', '')
        if 'eng' in language:
            langs.append('en')
        if 'fra' in language:
            langs.append('fr')
        if 'iku' in language:
            langs.append('iku')
        if 'zxx' in language:
            langs.append('zxx')
        r['language'] = langs

        if r['resource_type'] == 'app':
            r['related_type'] = 'application'

        if rec['type'] == 'info' and r['resource_type'] == 'file':
            r['resource_type'] = 'strategic_plan'
        else:
            r['resource_type'] = {
                None: 'dataset',
                'file': 'dataset',
                'doc': 'guide',
                'api': 'dataset',
                'app': 'dataset',
            }[r.get('resource_type', 'file')]

        r['format'] = resource_choices['format'].get(
            r['format'], r['format'])
        if r['format'] == 'app':
            r['format'] = 'other'

    _process.count[1] += 1
    logging.debug('Skipped {0}, processed {1}'.format(*_process.count))
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))
    return rec
_process.count = [0, 0]

def _main(fpath_jsonl_old):
    """
    With input JSONL data file, open and process a line at a time;
    """
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    with open(fpath_jsonl_old, 'rb') as fp_in:
        try:
            for line in fp_in:
                rec = _process(line.rstrip())
                if (rec):
                    print simplejson.dumps(rec)
        except IOError:
            print >> sys.stderr, (
                'Error: input file <{0}> not gzipped'.format(
                    fpath_jsonl_old))

def usage():
    """
    Display usage message
    """
    print >> sys.stderr, (
        'Usage: python {0} <in-file>'.format(sys.argv[0]))
    print >> sys.stderr, (
        'where <in-file> is a gzipped ckanext-canada@v2.1 metadata file')
    sys.exit(-1)

def _set_new_schema_dataset_choices():
    """
    Initialize tree of choices (label:value) for new schema dataset
    choice fields
    """
    def choice_mapping(f):
        old_new = {}
        for ch in f['choices']:
            old = ch.get('label', {'en': ch['value']})
            try:
                old = old['en']
            except TypeError:
                pass
            old = old.replace(',', '')
            value = ch['value']
            old_new[old] = value
            for r in ch.get('replaces', ()):
                old_new[r] = value
        return old_new

    ckan = LocalCKAN()
    sd_new = ckan.action.scheming_dataset_schema_show(type='dataset')
    dataset_choices.clear()
    for f in sd_new['dataset_fields']:
        if 'choices' in f:
            dataset_choices[f['field_name']] = choice_mapping(f)

    resource_choices.clear()
    for f in sd_new['resource_fields']:
        if 'choices' in f:
            resource_choices[f['field_name']] = choice_mapping(f)

def metadata_xform(fpath_jsonl_old):
    if path.islink(fpath_jsonl_old):
        fpath_jsonl_old = readlink(fpath_jsonl_old)
    if not path.isfile(fpath_jsonl_old):
        usage()

    # Input path must refer to a gzipped file
    fpath_jsonl_old = path.expanduser(
        path.expandvars(path.abspath(fpath_jsonl_old)))

    # Set dataset choice tree
    _set_new_schema_dataset_choices()

    # Process input file
    _main(fpath_jsonl_old)
