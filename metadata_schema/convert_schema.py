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
LANGS = 'en', 'fr'

# ('section name', [field name 1, ...]), ...
SECTIONS_FIELDS = [
    ("Metadata Record Information", [
        #'file_identifier', - unique ID, provided by ckan as 'id'
        #'date_stamp', - revisioned by ckan, get first revision_timestamp
        #'date_modified', - revisioned by ckan, get last revision_timestamp
        'language',
        #'name', - optional in proposed, REQUIRED here!
        'url',
        #'heirarchy_level', - doesn't apply, ckan has 1-n resources per
        'author',
        'author_email',
        'metadata_standard_name', # won't they all be the same?
        'catalog_type',
        ]),
    ("Dataset Identification Information", [
        'title',
        #'date', - doesn't apply, use resource created or last_modified
        #'data_modified', - doesn't apply, use resource last_modified
        #'date_type', doesn't apply, (see above) and use revisioned resources
        'info',
        #'status', use resource description (?) not appropriate?
        #'language', use resource name instead (?)
        'character_set', # poor name! text encoding is better. per resource?
        'maintenance_and_update_frequency',
        ]),
    ("Supplemental Information", [
        'program_url',
        'data_dictionary', # may end up as a resource
        'supplemental_information_other',
        #'additional_metadata', use extra fields instead
        ]),
    ("Data Series", [
        'data_series_name',
        'issue_identification', # related to 'name'/'url' above
        'data_series_url',
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
    ("Contact Information", [ # NOTE: these can't be repeated at the moment
        'individual_name',
        #'organization_name', - appears as 'author' above
        'position_name',
        'telephone_number_voice',
        'fax_number',
        'delivery_point_civic_address',
        'city',
        'state_province',
        'postal_code',
        'country',
        'maintainer_email',
        'online_resource',
        'hours_of_service',
        'roles',
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

# The field order here must match the proposed schema spreadsheet
ProposedField = namedtuple("ProposedField", """
    property_name
    iso_multiplicity
    gc_multiplicity
    description
    example
    nap_iso_19115_ref
    domain_best_practice
    """)

# 'proposed name' : 'new or existing CKAN field name'
PROPOSED_TO_EXISTING_FIELDS = {
    'dataset_uri_dataset_unique_identifier': 'url',
    'organization_name': 'author',
    'contact': 'author_email',
    'email': 'maintainer_email',
    'title': 'title',
    'abstract': 'info',
    'keyword': 'tags',
    }
EXISTING_FIELDS = set(PROPOSED_TO_EXISTING_FIELDS.values())

# 'new field name': '2012 field name'
FIELD_MAPPING = {
    'author_email': 'owner',
    'individual_name': 'contact_name',
    'position_name': 'contact_title',
    'telephone_number_voice': 'contact_phone',
    'maintainer_email': 'contact_email',
    'title': 'title_en',
    'author': 'department',
    'subject': 'category',
    'language': 'language__',
    'date': 'date_released',
    'date_modified': 'date_update',
    'maintenance_and_update_frequency': 'frequency',
    'info': 'description_en',
    'tags': 'keywords_en',
    'program_url': 'program_page_en', # note: different than French
    'data_series_url': 'data_series_url_en',
    'data_dictionary': 'dictionary_list:_en', # note: different than French
    'supplemental_information_other': 'supplementary_documentation_en',
    'geographic_region_name': 'Geographic_Region_Name',
    'begin_position': 'time_period_start',
    'end_position': 'time_period_end',
    'data_series_name': 'group_name_en',
    }


# 'new field name' : '2012 French field name'
BILINGUAL_FIELDS = {
    'title': 'title_fr',
    'info': 'description_fr',
    'tags': 'keywords_fr',
    'program_url': 'program_url_fr',
    'data_series_url': 'data_series_url_fr',
    'data_dictionary': 'data_dictionary_fr',
    'supplemental_information_other': 'supplementary_documentation_fr',
    'data_series_name': 'group_name_fr',
    }

def lang_versions(root, xp):
    """
    Return {'en': english_text, 'fr': french_text} dict for a given
    xpath xp.
    """
    out = {lang:root.xpath(xp + '[@xml:lang="%s"]' % lang)
        for lang in LANGS}
    assert out['en'], "Not found: %s" % xp
    assert out['fr'], "Not found: %s" % xp
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

            old_id_fr = BILINGUAL_FIELDS.get(field, None)
            if old_id_fr:
                new_field['pilot_id_fr'] = old_id_fr
            new_field['bilingual'] = bool(old_id_fr)

            new_section['fields'].append(new_field)
        schema_out['sections_fields'].append(new_section)

    return json.dumps(schema_out, sort_keys=True, indent=2)

print main()


