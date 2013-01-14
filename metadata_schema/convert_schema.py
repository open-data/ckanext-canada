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
from collections import namedtuple
from itertools import groupby

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.join(HERE, 'pilot')
OLD_SCHEMA_NAME = os.path.join(PILOT, 'metadata_schema.xml')
PROPOSED_SCHEMA_NAME = os.path.join(HERE, 'proposed', 'proposed_schema.xls')
PROPOSED_SCHEMA_SHEET = 'Metadata Schema'
LANGS = 'eng', 'fra'

# ('section name', [field name 1, ...]), ...
SECTIONS_FIELDS = [
    ("Metadata Record Information", [
        #'file_identifier', - unique ID, provided by ckan as 'id'
        #'date_stamp', - revisioned by ckan, get first revision_timestamp
        #'date_modified', - revisioned by ckan, get last revision_timestamp
        #'language', - XXX EXPORT ONLY - Always "eng; CAN, fra; CAN"
        'name', #- optional in proposed, REQUIRED here!
        #'heirarchy_level', - doesn't apply, ckan has 1-n resources per
        'author', # XXX set to GC Department (ckan group), no data entry
        'author_email', # XXX set to single common email, no data entry
        #'metadata_standard_name', - XXX EXPORT ONLY - Always same for all
        'catalog_type', # will control field validation in the future
        ]),
    ("Dataset Identification Information", [
        'title',
        #'date', - doesn't apply, use resource created or last_modified
        #'data_modified', - doesn't apply, use resource last_modified
        #'date_type', doesn't apply, (see above) and use revisioned resources
        'notes',
        #'status', use resource description (?) not appropriate?
        #'character_set', not req'd: UTF-8 is our new standard encoding :-)
        ]),
    ("Supplemental Information", [
        'program_url',
        #'data_dictionary', stored as resources
        'supplemental_information_other',
        #'additional_metadata', not required (use supplemental..other field)
        ]),
    ("Data Series", [
        'data_series_name',
        'issue_identification', # related to 'name'/'url' above
        'url',
        ]),
    ("Thesaurus-GC Core Subject Thesaurus", [
        'subject', # TODO: create tag vocabulary for this
        #'title', - no place for these at the moment
        #'date',
        #'date_type',
        #'organization_name',
        ]),
    ("Thesaurus-ISO Topic Category", [
        'topic_category', # TODO: create tag vocabulary for this
        #'title', - no place for these at the moment
        #'date',
        #'date_type',
        #'organization_name',
        ]),
    ("Descriptive Keywords", [
        'tags',
        #'type', - no place for this at the moment
        ]),
    ("Extent", [
        'begin_position', # need to investigate searching
        'end_position',
        'geographic_region_name',
        #'north_bound_latitude', - these are handled by ckanext-spacial
        #'south_bound_latitude',
        #'west_bound_longitude',
        #'east_bound_longitude',
        ]),
    #("Constraints", [
        #'legal_access_constraints', - handled by 'license_id'
        #'legal_use_constraints',
        #]),
    #("Distribution Information", [ - these are handled by resources
        #'linkage_url', - resource.url
        #'transfer_size', - resource.size
        #'protocol', - part of resource.url
        #'description', - resource.description
        #'format_name', - resource.resource_type
        #'format_version', - part of resource.resource_type (?)
    ]

# Resource fields (no sections)
RESOURCE_FIELDS = [
    'url',
    'size',
    'format',
    'language',
    'maintenance_and_update_frequency',
    ]

EXISTING_RESOURCE_FIELDS = [
    'url',
    'format',
    'size',
    ]

# The field order here must match the proposed schema spreadsheet
ProposedField = namedtuple("ProposedField", """
    languages
    property_name
    iso_multiplicity
    gc_multiplicity
    description
    example
    nap_iso_19115_ref
    domain_best_practice
    controlled_vocabulary_reference_eng
    controlled_vocabulary_reference_fra
    implementation_plan
    """)

# 'proposed name' : 'new or existing CKAN field name'
PROPOSED_TO_EXISTING_FIELDS = {
    'dataset_uri_dataset_unique_identifier': 'name',
    'organization_name': 'author',
    'contact': 'author_email',
    'email': 'maintainer_email',
    'title': 'title',
    'abstract': 'notes',
    'keyword': 'tags',
    'data_series_url': 'url',
    }
EXISTING_FIELDS = set(PROPOSED_TO_EXISTING_FIELDS.values())

# FOR IMPORTING ENGLISH FIELDS FROM PILOT
# 'new field name': 'pilot field name'
FIELD_MAPPING = {
    'author_email': 'owner',
    'individual_name': 'contact_name',
    'position_name': 'contact_title',
    'telephone_number_voice': 'contact_phone',
    'maintainer_email': 'contact_email',
    'title': 'title_en',
    'author': 'department', # FIXME: will this be replaced by group owner?
    'subject': 'category',
    'language': 'language__',
    'date': 'date_released',
    'date_modified': 'date_update',
    'maintenance_and_update_frequency': 'frequency',
    'notes': 'description_en',
    'tags': 'keywords_en',
    'program_url': 'program_page_en', # note: different than French
    'url': 'data_series_url_en',
    'data_dictionary': 'dictionary_list:_en', # note: different than French
    'supplemental_information_other': 'supplementary_documentation_en',
    'geographic_region_name': 'Geographic_Region_Name',
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
    'program_url': 'program_url_fr',
    'url': 'data_series_url_fr',
    'data_dictionary': 'data_dictionary_fr',
    'supplemental_information_other': 'supplementary_documentation_fr',
    'data_series_name': 'group_name_fr',
    'issue_identification': None,
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
    for i in range(sheet.nrows):
        row = sheet.row(i)
        p = ProposedField(*(unicode(f.value).strip() for f in row))
        if not p.description and not p.gc_multiplicity:
            # skip the header rows
            continue
        new_name = proposed_name_to_identifier(p.property_name)
        new_name = PROPOSED_TO_EXISTING_FIELDS.get(new_name, new_name)
        assert new_name not in p, new_name
        out[new_name] = p
    return out

def main():
    schema_out = {
        'sections_fields': [],
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
            'description': {'en': proposed[section_name].description},
            'fields': [],
            }

        for field in fields:
            p = proposed[field]
            new_field = { # FIXME: French?
                'id': field,
                'proposed_name': {'en': p.property_name},
                'iso_multiplicity': p.iso_multiplicity,
                'gc_multiplicity': p.gc_multiplicity,
                'description': {'en': p.description},
                'example': p.example,
                'nap_iso_19115_ref': p.nap_iso_19115_ref,
                'domain_best_practice': {'en': p.domain_best_practice},
                'existing': field in EXISTING_FIELDS,
                'controlled_vocabulary_reference_eng':
                    p.controlled_vocabulary_reference_eng,
                'controlled_vocabulary_reference_fra':
                    p.controlled_vocabulary_reference_fra,
                }
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
            new_field['bilingual'] = bool(old_id_fra)

            new_section['fields'].append(new_field)
        schema_out['sections_fields'].append(new_section)

    return json.dumps(schema_out, sort_keys=True, indent=2)

print main()


