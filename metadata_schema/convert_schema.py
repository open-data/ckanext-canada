#!/usr/bin/env python

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
PROPOSED_SCHEMA_STARTS_ROW = 7
LANGS = 'eng', 'fra'

# ('section name', [field name 1, ...]), ...
SECTIONS_FIELDS = [
    ("Metadata Record Information", [
        'id', # unique ID,
        #'language', - Always "eng; CAN|fra; CAN"
        'author', # XXX set to GC Department (ckan group), no data entry
        'department_number', # generated from GC Department
        #'author_email', - XXX set to single common email, no data entry
        'name', #- optional in proposed, REQUIRED here!
        'digital_object_identifier', # "datacite" identifier
        'catalog_type', # will control field validation in the future
        ]),
    ("Identification Information", [
        'title',
        'notes',
        'subject', # TODO: create tag vocabulary for this
        'topic_category', # TODO: create tag vocabulary for this
        'tags',
        'maintenance_and_update_frequency',
        'temporal_element',
        'geographic_region',
        'data_series_name',
        'data_series_issue_identification',
        'documentation_url',
        'related_document_url',
        'url',
        'license_id',
        ]),
    ("Geospatial Additional Fields", [
        'spatial_representation_type',
        'presentation_form',
        'the_geom', # spatial extension
        'browse_graphic_url',
        ]),
    ]

# Resource fields (no sections)
RESOURCE_FIELDS = [
    'url',
    'name',
    'size',
    'format',
    'language',
    'date_published', # ADMIN-only field that will control publishing
    'last_modified',
    ]

EXISTING_RESOURCE_FIELDS = set(default_resource_schema())

BILINGUAL_RESOURCE_FIELDS = set([
    'name',
    ])

EXISTING_FIELDS = set(default_package_schema()
    ) | set(['the_geom'])

# The field order here must match the proposed schema spreadsheet
ProposedField = namedtuple("ProposedField", """
    class_
    sub_class
    property_name
    iso_multiplicity
    gc_multiplicity
    type_
    description
    example
    nap_iso_19115_ref
    domain_best_practice
    controlled_vocabulary_reference_eng
    controlled_vocabulary_reference_fra
    implementation_old
    implementation
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
    'electronicMailAddress': 'author_email',
    'dataSetURI': 'name',
    'digitalObjectIdentifier': 'digital_object_identifier',
    'catalogueType': 'catalog_type',
    'title': 'title',
    'datePublished': 'resource:date_published',
    'dateModified': 'resource:last_modified',
    'abstract': 'notes',
    'subject': 'subject',
    'topicCategory': 'topic_category',
    'keyword': 'tags',
    'maintenanceAndUpdateFrequency':
        'maintenance_and_update_frequency',
    'temporalElement': 'temporal_element',
    'geographicRegion': 'geographic_region',
    'spatial': 'the_geom',
    'dataSeriesName': 'data_series_name',
    'issueIdentification': 'data_series_issue_identification',
    #'supplementalInformation': 'supplemental_information', - no applicable mapping
    'documentationUrl': 'documentation_url',
    'relatedDocuments': 'related_document_url',
    'programURL': 'url',
    'Licence': 'license_id',
    'URL': 'resource:url',
    #'language2': 'resource:language',
    'language': 'resource:language',
    # resource fields
    'transferSize': 'resource:size',
    'formatName': 'resource:format',

    'spatialRespresentionType': 'spatial_representation_type',
    'presentationForm': 'presentation_form',
    #'polygon' DEFER
    'browseGraphicFileName': 'browse_graphic_url',
    }

# FOR IMPORTING ENGLISH FIELDS FROM PILOT
# 'new field name': 'pilot field name'
FIELD_MAPPING = {
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
    }

def lang_versions(root, xp):
    """
    Return {'eng': english_text, 'fra': french_text} dict for a given
    xpath xp.
    """
    out = {lang:root.xpath(xp + '[@xml:lang="%s"]' % lang[:2])
        for lang in LANGS}
    assert all(out[lang] for lang in LANGS), "Not all langs found: %s" % xp
    return {k:v[0].text for k, v in out.items()}

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

def read_proposed_fields():
    """
    Return a dict containing:
    {'new field name': ProposedField(...), ...}
    """
    workbook = xlrd.open_workbook(PROPOSED_SCHEMA_NAME)
    sheet = workbook.sheet_by_name(PROPOSED_SCHEMA_SHEET)
    out = {}
    for i in range(PROPOSED_SCHEMA_STARTS_ROW, sheet.nrows):
        row = sheet.row(i)
        p = ProposedField(*(unicode(f.value).strip() for f in row))
        if not p.description and not p.type_:
            # skip the header rows
            continue
        new_name = p.property_name.strip()
        new_name = PROPOSED_TO_EXISTING_FIELDS.get(new_name, new_name)
        if new_name in out:
            new_name = PROPOSED_TO_EXISTING_FIELDS.get(new_name + '2',
                new_name) # language is duplicated
        assert new_name not in out, (new_name, out.keys())
        out[new_name] = p
    return out

def field_from_proposed(p):
    "extract proposed field information into a field dict"
    return {
        'proposed_name': {'en': p.property_name},
        'proposed_type': p.type_,
        'iso_multiplicity': p.iso_multiplicity,
        'gc_multiplicity': p.gc_multiplicity,
        'description': {'en': p.description},
        'example': p.example,
        'nap_iso_19115_ref': p.nap_iso_19115_ref,
        'domain_best_practice': {'en': p.domain_best_practice},
        'controlled_vocabulary_reference_eng':
            p.controlled_vocabulary_reference_eng,
        'controlled_vocabulary_reference_fra':
            p.controlled_vocabulary_reference_fra,
        'implementation': p.implementation,
        'data_gov_common_core': p.data_gov_common_core,
        'rdfa_lite': p.rdfa_lite,
        }

def camelcase_to_proper_name(name):
    """
    >>> camelcase_to_proper_name(u"imageryBaseMapsEarthCover")
    u"Imagery Base Maps Earth Cover"
    """
    # NOTE: this doesn't work if the uppercase letter is non-ascii
    return re.sub(r'([A-Z])', r' \1', name).title()

def apply_field_customizations(schema_out):
    """
    Make customizations to fields not extracted from proposed
    or pilot information
    """
    schema_out['vocabularies'] = {
        vocabularies.VOCABULARY_GC_CORE_SUBJECT_THESAURUS: 'subject',
        vocabularies.VOCABULARY_ISO_TOPIC_CATEGORIES: 'topic_category',
        }

    def get_field(field_id):
        (field,) = (f
            for s in schema_out['dataset_sections']
            for f in s['fields']
            if f['id'] == field_id)
        return field

    subject = get_field('subject')
    subject['type'] = 'keywords'
    for k, eng in sorted(vocabularies.GC_CORE_SUBJECT_THESAURUS['eng'].items()):

        if k not in vocabularies.GC_CORE_SUBJECT_THESAURUS['fra']:
            continue # no "form descriptors" in french

        (target,) = (c for c in subject['choices'] if c['eng'] == eng)
        target['id'] = k

    topic_category = get_field('topic_category')
    topic_category['type'] = 'keywords'
    topic_category['choices'] = [{
            'id': eng[:3],
            'eng': camelcase_to_proper_name(eng),
            'fra': camelcase_to_proper_name(fra),
            }
            for eng, fra in zip(
                vocabularies.ISO_TOPIC_CATEGORIES['eng'],
                vocabularies.ISO_TOPIC_CATEGORIES['fra'],
            )
        ]



def main():
    schema_out = {
        'dataset_sections': [],
        'resource_fields': [],
        'languages': list(LANGS),
        }

    proposed = read_proposed_fields()

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
            f = FIELD_MAPPING.get(field)
            if f:
                xp = '//item[inputname="%s"]' % f
                new_field.update({
                    'pilot_id': f,
                    'name': lang_versions(old_root, xp + '/name'),
                    'help': lang_versions(old_root, xp + '/helpcontext'),
                    'type': "".join(old_root.xpath(xp +
                        '/type1/inputtype[1]/text()')),
                    })
                if not new_field['type']:
                    # this seems to indicate a selection from a list
                    new_field['choices'] = pilot_choices(f)
                    new_field['type'] = 'choice'

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
        schema_out['resource_fields'].append(new_rfield)

    apply_field_customizations(schema_out)

    return json.dumps(schema_out, sort_keys=True, indent=2)

print main()


