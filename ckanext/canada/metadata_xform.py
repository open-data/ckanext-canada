"""
Transform metadata .jsonl file from CKAN 2.1 alignment to 2.3
"""
import logging
import sys

import simplejson

from ckanapi import LocalCKAN

SUFFIX_FRA = '_fra'
LEN_SUFFIX_FRA = len(SUFFIX_FRA)
LANG_KEYS = ('en', 'fr')
SP_SP = '  '
SP_PIPE_SP = ' | '
CANSIM_ROOT = 'http://www5.statcan.gc.ca/cansim/home-accueil?lang=eng'
SUMMARY_ROOT = 'http://www.statcan.gc.ca/tables-tableaux/sum-som/'

# new schema description, data field choices
dataset_choices = {}
resource_choices = {}


def _process(line, portal=False):
    """
    Process one JSONL record of input, return None if Geo data and
    metadata in alignment with ckan-2.3 otherwise
    """
    rec = simplejson.loads(line)

    logging.debug('Before:')
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))

    if not portal:
        if rec.get('catalog_type', '').startswith('Geo'):
            return

        # Don't inclued CANSIM records.
        if rec.get('url') == CANSIM_ROOT:
            return

        if rec.get('url') and rec['url'].startswith(SUMMARY_ROOT):
            return

    if rec['type'] not in ('info', 'dataset'):
        return

    if rec['type'] == 'info':
        rec['collection'] = u'publication'
    elif rec.get('catalog_type', '').startswith('Geo'):
        rec['collection'] = u'geogratis'
    else:
        rec['collection'] = u'primary'
    rec['jurisdiction'] = u'federal'
    rec['restrictions'] = u'unrestricted'
    rec['imso_approval'] = (
        u'true' if rec.get('portal_release_date') else u'false'
    )

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
    if rec['collection'] == u'geogratis':
        if not rec['keywords']['fr']:
            rec['keywords']['fr'] = [u'g\u00e9ogratis', u'g\u00e9ospatiale']
        if not rec['keywords']['en']:
            rec['keywords']['en'] = [u'geogratis', u'geospatial']

    # convert subject english-sp-sp-french content to fluent text
    if '  ' in rec.get('subject', [''])[0]:
        rec['subject'] = [
            dataset_choices['subject'][s.lstrip().split(SP_SP, 1)[0]]
            for s in rec.get('subject', [])
        ]

    rec['topic_category'] = [
        dataset_choices['topic_category'][s.lstrip().split(SP_SP, 1)[0]]
        for s in rec.get('topic_category', [])
    ]

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
        for gr in rec.get('geographic_region', [])]

    if rec.get('spatial_representation_type'):
        rec['spatial_representation_type'] = [
            dataset_choices['spatial_representation_type'][
                rec['spatial_representation_type'].lstrip().split(
                    SP_PIPE_SP, 1)[0]]]
    else:
        rec['spatial_representation_type'] = []

    if rec['collection'] == u'geogratis':
        rec['maintainer_email'] = 'NRCan.geogratis-geogratis.RNCan@canada.ca'

    rec['ready_to_publish'] = str(rec.get('ready_to_publish', 'false')).lower()

    if 'title_translated' not in rec:
        rec['title_translated'] = rec.pop('title')
    if 'notes_translated' not in rec:
        rec['notes_translated'] = rec.pop('notes')

    rec.pop('extras', None)

    # merge per-resource name, name_fra to fluent text
    if not 'resources' in rec:
        print >> sys.stderr, ('No resources')
        _process.count[0] += 1
        return
    for r in rec['resources']:
        if 'name_fra' in r:
            r['name_translated'] = dict(
                zip(LANG_KEYS, (r.pop('name', None), r.pop('name_fra', None))))
        elif 'name_translated' not in r:
            r['name_translated'] = r.pop('name')

        langs = []
        language = r.get('language', '')
        if not isinstance(language, list):
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
            trans = {
                None: 'dataset',
                'file': 'dataset',
                'doc': 'guide',
                'api': 'dataset',
                'app': 'dataset',
            }
            typ = r.get('resource_type', 'file')
            if typ in trans:
                r['resource_type'] = trans[typ]

        r['format'] = resource_choices['format'].get(
            r['format'], r['format'])
        if r['format'] == 'app':
            r['format'] = 'other'

    _process.count[1] += 1
    logging.debug('Skipped {0}, processed {1}'.format(*_process.count))
    logging.debug(simplejson.dumps(rec, indent=4 * ' '))
    return rec
_process.count = [0, 0]


def _main(portal):
    """
    With input JSONL data file, open and process a line at a time;
    """
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    try:
        for line in sys.stdin:
            rec = _process(line.rstrip(), portal)
            if (rec):
                print simplejson.dumps(rec)
    except IOError:
        print >> sys.stderr, 'Error while reading line.'


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


def metadata_xform(portal):
    # Set dataset choice tree
    _set_new_schema_dataset_choices()

    # Process input file
    _main(portal)
