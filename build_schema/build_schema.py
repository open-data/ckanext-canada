#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
This script is used for a "one-time" conversion from the 2012 data.gc.ca
schema described by .xml files in this directory to the new metadata
schema description as .json output on stdout.
"""

import json
import lxml.etree
import xlrd
import os
import re
from collections import namedtuple
from itertools import groupby

from ckan.logic.schema import default_package_schema, default_resource_schema

import vocabularies

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.join(HERE, 'pilot')
OLD_SCHEMA_NAME = os.path.join(PILOT, 'metadata_schema.xml')
PROPOSED_SCHEMA_NAME = os.path.join(HERE, 'proposed', 'proposed_schema.xls')
PROPOSED_SCHEMA_SHEET = 'Metadata Schema'
PROPOSED_VOCABULARY_SHEET = 'Controlled Vocabulary'
PROPOSED_SCHEMA_STARTS_ROW = 7
LANGS = 'eng', 'fra'

# ('section name', [field name 1, ...]), ...
SECTIONS_FIELDS = [
    ("Primary Fields", [
        'id', # unique ID,
        'language', # Always "eng; CAN|fra; CAN"
        'author', # XXX set to GC Department (ckan group), no data entry
        'department_number', # generated from GC Department
        'author_email', # XXX set to single common email, no data entry
        'title',
        'name', #- optional in proposed, REQUIRED here!
        'notes',
        'digital_object_identifier', # "datacite" identifier
        'catalog_type', # will control field validation in the future
        'subject', 
        'topic_category', 
        'tags',
        'license_id',
        'data_series_name',
        'data_series_issue_identification',
        'date_published', # ADMIN-only field that will control publishing
        ]),
    ("Additional Fields", [
        'maintenance_and_update_frequency',
        'time_period_coverage_start',
        'time_period_coverage_end',
        'geographic_region',
        'url',
        'endpoint_url',
        'ready_to_publish',
        ]),
    ("Geospatial Additional Fields", [
        'spatial_representation_type',
        'presentation_form',
        'spatial',
        'browse_graphic_url',
        ]),
    ]

# override calculated values
FIELD_OVERRIDES = {
    'tags': {'bilingual': False},
    'resource:resource_type': {'choices': [ # should match normal CKAN values
        {'eng': 'File', 'fra': 'File', 'key': 'file'},
        {'eng': 'Doc', 'fra': 'Doc', 'key': 'doc'},
        {'eng': 'API', 'fra': 'API', 'key': 'api'},
        ]},
    }

# Resource fields (no sections)
RESOURCE_FIELDS = [
    'resource_type',
    'url',
    'size',
    'format',
    'language',
    'last_modified',
    ]

EXISTING_RESOURCE_FIELDS = set(default_resource_schema())

BILINGUAL_RESOURCE_FIELDS = set([
    ])

EXISTING_FIELDS = set(default_package_schema()
    ) | set(['spatial'])

# The field order here must match the proposed schema spreadsheet
ProposedField = namedtuple("ProposedField", """
    class_
    sub_class
    property_name
    property_label
    iso_multiplicity
    property_name_fra
    property_label_fra
    gc_multiplicity
    type_
    description
    description_fra
    example
    domain_best_practice
    name_space
    implementation
    implementation_fra
    data_gov_common_core
    json
    rdfa_lite
    """)

# 'proposed name' : 'new or existing CKAN field name'
# other dataset fields that match are assumed to be
# the same as their proposed fields
PROPOSED_TO_EXISTING_FIELDS = {
    'fileIdentifier': 'id',
    'organizationName': 'author',
    'departmentNumber': 'department_number',
    'electronicMail Address': 'author_email',
    'dataSetURI': 'name',
    'digitalObjectIdentifier': 'digital_object_identifier',
    'catalogueType': 'catalog_type',
    'title': 'title',
    'datePublished': 'date_published',
    'readyToPublish': 'ready_to_publish',
    'dateModified': 'resource:last_modified',
    'abstract': 'notes',
    'subject': 'subject',
    'topicCategory': 'topic_category',
    'keywords': 'tags',
    'maintenanceAndUpdateFrequency':
        'maintenance_and_update_frequency',
    'timePeriodCoverageStart': 'time_period_coverage_start',
    'timePeriodCoverageEnd': 'time_period_coverage_end',
    'geographicRegion': 'geographic_region',
    'dataSeriesName': 'data_series_name',
    'issueIdentification': 'data_series_issue_identification',
    #'supplementalInformation': 'supplemental_information', - no applicable mapping
    'documentationURL': 'documentation_url',
    'relatedDocumentsURL': 'related_document_url',
    'programURL': 'url',
    'endpoint': 'endpoint_url',
    'license': 'license_id',
    'accessURL': 'resource:url',
    'language2': 'resource:language',
    # resource fields
    'transferSize': 'resource:size',
    'formatName': 'resource:format',

    'spatialRespresentionType': 'spatial_representation_type',
    'presentationForm': 'presentation_form',
    'resourceType': 'resource:resource_type',
    #'polygon' DEFER
    'browseGraphicFileName': 'browse_graphic_url',
    }

# FOR IMPORTING ENGLISH FIELDS FROM PILOT
# 'new field name': 'pilot field name'
PILOT_FIELD_MAPPING = {
    #'author_email': 'owner',
    'individual_name': 'contact_name',
    'position_name': 'contact_title',
    'telephone_number_voice': 'contact_phone',
    #'maintainer_email': 'contact_email', - will have a single common email
    'title': 'title_en',
    'author': 'department', # FIXME: will this be replaced by group owner?
    'subject': 'category',
    'language': 'language__',
    'date': 'date_released',
    'date_modified': 'date_update',
    'maintenance_and_update_frequency': 'frequency',
    'notes': 'description_en',
    'tags': 'keywords_en',
    'url': 'program_page_en', # note: different than French
    'documentation_url': 'data_series_url_en',
    'data_dictionary': 'dictionary_list:_en', # note: different than French
    'supplemental_information': 'supplementary_documentation_en',
    'geographic_region': 'Geographic_Region_Name',
    'begin_position': 'time_period_start',
    'end_position': 'time_period_end',
    'data_series_name': 'group_name_en',
    'resource:url': 'dataset_link_en_1',
    'resource:format': 'dataset_format_1',
    'resource:size': 'dataset_size_en_1',
    }

# FOR IMPORTING FRENCH FIELDS FROM PILOT,
# and marking French fields (value=None)
# 'new field name' : 'pilot field name'
BILINGUAL_FIELDS = {
    'title': 'title_fr',
    'notes': 'description_fr',
    'tags': 'keywords_fr',
    'url': 'program_url_fr',
    'documentation_url': 'data_series_url_fr',
    'data_dictionary': 'data_dictionary_fr',
    'supplemental_information': 'supplementary_documentation_fr',
    'data_series_name': 'group_name_fr',
    'data_series_issue_identification': None,
    'issue_identification': None,
    'related_document_url': None,
    'endpoint_url': None,
    }

def lang_versions(root, xp):
    """
    Return {'eng': english_text, 'fra': french_text} dict for a given
    xpath xp.
    """
    out = dict((lang, root.xpath(xp + '[@xml:lang="%s"]' % lang[:2]))
        for lang in LANGS)
    assert all(out[lang] for lang in LANGS), "Not all langs found: %s" % xp
    return dict((k, v[0].text) for k, v in out.items())

def pilot_choices(name):
    """
    Return a list of the choices from <name>.xml like:
    [{'pilot_uuid': ..., 'en': ..., 'fr': ... }, ...]
    """
    choices = []
    with open(os.path.join(PILOT, name + '.xml')) as c:
        croot = lxml.etree.parse(c)
        for node in croot.xpath('/root/item'):
            option = lang_versions(node, 'name')
            option['pilot_uuid'] = node.get('id')
            choices.append(option)
    return choices

def proposed_name_to_identifier(name):
    """
    Convert a proposed name with spaces, punctuation and capital letters
    to a valid identifier with only lowercase letters and underscores

    >>> proposed_name_to_identifier('Proposed Metadata Fields for data.gc.ca')
    'proposed_metadata_fields_for_data_gc_ca'
    """
    words = (g for alpha, g in groupby(name, lambda c: c.isalpha()) if alpha)
    return "_".join("".join(g).lower() for g in words)

def read_proposed_fields_vocab():
    """
    Return (proposed field dict, vocabulary dict)
    """
    workbook = xlrd.open_workbook(PROPOSED_SCHEMA_NAME)
    vocab = vocabularies.read_from_sheet(
        workbook.sheet_by_name(PROPOSED_VOCABULARY_SHEET))

    sheet = workbook.sheet_by_name(PROPOSED_SCHEMA_SHEET)
    out = {}
    for i in range(PROPOSED_SCHEMA_STARTS_ROW, sheet.nrows):
        row = sheet.row(i)
        values = []
        for f in row:
            if f.ctype == xlrd.XL_CELL_DATE:
                values.append("%04d-%02d-%02d" %
                    xlrd.xldate_as_tuple(f.value, workbook.datemode)[:3])
            elif f.ctype == xlrd.XL_CELL_NUMBER:
                values.append(int(f.value))
            else:
                values.append(f.value)
        p = ProposedField(*(unicode(v).strip() for v in values))

        if not p.description and not p.type_:
            # skip the header rows
            continue
        new_name = p.property_name.strip()
        if not new_name:
            continue
        new_name = PROPOSED_TO_EXISTING_FIELDS.get(new_name, new_name)
        if new_name in out:
            new_name = PROPOSED_TO_EXISTING_FIELDS.get(new_name + '2',
                new_name) # language is duplicated
        assert new_name not in out, (new_name, out.keys())
        out[new_name] = p
    return out, dict((PROPOSED_TO_EXISTING_FIELDS.get(k, k), v)
        for k,v in vocab.iteritems())

def field_from_proposed(p):
    "extract proposed field information into a field dict"
    return {
        'proposed_name': {'eng': p.property_name, 'fra': p.property_name_fra},
        'proposed_type': p.type_,
        'gc_multiplicity': p.gc_multiplicity,
        'description': {'eng': p.description, 'fra': p.description_fra},
        'example': p.example,
        'label': {'eng': p.property_label, 'fra': p.property_label_fra},
        }

def apply_field_customizations(schema_out, vocab):
    """
    Make customizations to fields not extracted from proposed
    or pilot information
    """
    schema_out['vocabularies'] = {
        vocabularies.VOCABULARY_GC_CORE_SUBJECT_THESAURUS: 'subject',
        vocabularies.VOCABULARY_ISO_TOPIC_CATEGORIES: 'topic_category',
        vocabularies.VOCABULARY_GC_GEOGRAPHIC_REGION: 'geographic_region',
        }

    def get_field(field_id):
        (field,) = (f
            for s in schema_out['dataset_sections']
            for f in s['fields']
            if f['id'] == field_id)
        return field

    def get_resource_field(field_id):
        (field,) = (f
            for f in schema_out['resource_fields']
            if f['id'] == field_id)
        return field

    subject = get_field('subject')
    subject['type'] = 'keywords'

    topic_category = get_field('topic_category')
    topic_category['type'] = 'keywords'

    def merge(c1, c2):
        def norm(t):
            if t == "Shapefile":
                return "SHP"
            return t.split('/')[0].strip()[:35]
        out = []
        ekeys = {}
        for d in c1:
            od = dict(d)
            out.append(od)
            ekeys[norm(od['eng'])] = od
        for d in c2:
            target = ekeys.get(norm(d['eng']))
            if target:
                target.update(d)
            else:
                out.append(d)
        return out

    for field, choices in vocab.iteritems():
        if field == 'language':
            f = get_resource_field('language')
        elif field.startswith('resource:'):
            f = get_resource_field(field[9:])
        else:
            f = get_field(field)

        if field in ('geographic_region',):
            # prefer proposed.xls ordering
            choices = merge(choices, f['choices'])
        elif 'choices' in f:
            choices = merge(f['choices'], choices)
        f['choices'] = choices


def apply_field_overrides(schema_out):
    """
    Apply fixes to proposed data from FIELD_OVERRIDES
    """
    for section in schema_out['dataset_sections']:
        for f in section['fields']:
            f.update(FIELD_OVERRIDES.get(f['id'], {}))
    for f in schema_out['resource_fields']:
        f.update(FIELD_OVERRIDES.get('resource:' + f['id'], {}))

def clean_tag_part(t):
    """
    Remove all special characters not accepted in tags and collapse
    all spaces to a single space
    """
    return u''.join(re.findall(u' ?[\w\-.]+', t, re.UNICODE)).lstrip()

def add_keys_for_choices(f):
    """
    Add a 'key' key to each choice in f['choices'] that will be used
    as the value to actually store in the DB + use with the API
    """
    if f.get('type') == 'keywords':
        for c in f['choices']:
            # keywords have strict limits on valid characters
            c['key'] = u'  '.join(clean_tag_part(c[lang]) for lang in LANGS)
    else:
        for c in f['choices']:
            # use the text itself for now (both when different)
            c['key'] = c[LANGS[0]]
            if c['key'] != c[LANGS[1]]:
                c['key'] += ' | ' + c[LANGS[1]]

def field_from_pilot(field_name, old_root):
    f = PILOT_FIELD_MAPPING.get(field_name)
    if not f:
        return {}

    xp = '//item[inputname="%s"]' % f
    new_field = {
        'pilot_id': f,
        'pilot_name': lang_versions(old_root, xp + '/name'),
        'pilot_help': lang_versions(old_root, xp + '/helpcontext'),
        'pilot_type': "".join(old_root.xpath(xp +
            '/type1/inputtype[1]/text()')),
        }
    if not new_field['pilot_type']:
        # this seems to indicate a selection from a list
        new_field['choices'] = pilot_choices(f)
        new_field['pilot_type'] = 'choice'
    return new_field


def main():
    schema_out = {
        'dataset_sections': [],
        'resource_fields': [],
        'languages': list(LANGS),
        }

    proposed, vocab = read_proposed_fields_vocab()

    with open(OLD_SCHEMA_NAME) as s:
        old_root = lxml.etree.parse(s)

    schema_out['intro'] = lang_versions(old_root, '//intro')

    for section, fields in SECTIONS_FIELDS:
        section_name = proposed_name_to_identifier(section)
        new_section = {
            'name': {'en': section}, # FIXME: French?
            'description': {}, # no longer available
            'fields': [],
            }

        for field in fields:
            p = proposed[field]
            new_field = field_from_proposed(p)
            new_field['id'] = field
            new_field['existing'] = field in EXISTING_FIELDS
            new_field.update(field_from_pilot(field, old_root))

            old_id_fra = BILINGUAL_FIELDS.get(field, None)
            if old_id_fra:
                new_field['pilot_id_fra'] = old_id_fra
            new_field['bilingual'] = field in BILINGUAL_FIELDS

            new_section['fields'].append(new_field)
        schema_out['dataset_sections'].append(new_section)

    for rfield in RESOURCE_FIELDS:
        new_rfield = {
            'id': rfield,
            'existing': rfield in EXISTING_RESOURCE_FIELDS,
            'bilingual': rfield in BILINGUAL_RESOURCE_FIELDS,
            }
        p = proposed.get('resource:' + rfield, None)
        if p:
            new_rfield.update(field_from_proposed(p))
        new_rfield.update(field_from_pilot('resource:' + rfield, old_root))
        schema_out['resource_fields'].append(new_rfield)

    apply_field_customizations(schema_out, vocab)

    # add keys for choices
    for f in schema_out['resource_fields'] + [df
            for sec in schema_out['dataset_sections']
            for df in sec['fields']]:
        if 'choices' not in f:
            continue
        add_keys_for_choices(f)

    apply_field_overrides(schema_out)

    return json.dumps(schema_out, sort_keys=True, indent=2)

print main()


