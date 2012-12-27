#!/usr/bin/env python

"""
This script is used for a "one-time" conversion from the 2012 data.gc.ca
schema described by .xml files in this directory to the new metadata
schema description as .json output on stdout.
"""

import json
import lxml.etree
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_GC_CA_2012 = os.path.join(HERE, 'data_gc_ca_2012')
SCHEMA_NAME = os.path.join(DATA_GC_CA_2012, 'metadata_schema.xml')
LANGS = 'en', 'fr'

# ('section name', [field name 1, ...]), ...
SECTIONS_FIELDS = [
    ("Metadata Record Information", [
        'author_email',
        ]),
    ("Dataset Identification Information", [
        'title',
        'date',
        'info',
        'language',
        'thesaurus',
        'maintenance_and_update_frequency',
        ]),
    ("Supplemental Information", [
        'program_url',
        'data_dictionary',
        'supplemental_information_other',
        ]),
    ("Data Series", [
        'data_series_name',
# (see XXX below): 'issue_identification',
        'url',
        ]),
    ("Descriptive Keywords", [
        'tags',
        ]),
    ("Contact Information", [
        'individual_name',
        'organization_name',
        'position_name',
        'telephone_number_voice',
        'maintainer_email',
        ]),
    ("Time Period", [
        'begin_position',
        'end_position',
        ]),
    ]

# 'new field name': '2012 field name'
FIELD_MAPPING = {
    'author_email': 'owner', # existing, was 'Contact'
    'individual_name': 'contact_name',
    'position_name': 'contact_title',
    'telephone_number_voice': 'contact_phone',
    'maintainer_email': 'contact_email', # existing, was 'Email'
    'title': 'title_en', # existing
    'organization_name': 'department',
    'thesaurus': 'category',
    'language': 'language__',
    'date': 'date_released',
    'date_modified': 'date_update',
    'maintenance_and_update_frequency': 'frequency',
    'info': 'description_en', # existing, was 'Abstract'
    'tags': 'keywords_en', # existing, was 'Keywords'
    'program_url': 'program_page_en',
    'url': 'data_series_url_en', # existing, was 'Data Series URL'
    'data_dictionary': 'dictionary_list:_en',
    'supplemental_information_other': 'supplementary_documentation_en',
    'geographic_region_name': 'Geographic_Region_Name',
    'begin_position': 'time_period_start',
    'end_position': 'time_period_end',
    'data_series_name': 'group_name_en',
# XXX doesn't seem right: 'number_datasets': 'issue_identification',
    }


# 'new field name' : '2012 French field name'
BILINGUAL_FIELDS = {
    'title': 'title_fr',
    'info': 'description_fr',
    'tags': 'keywords_fr',
    'program_url': 'program_url_fr', # note: different than english
    'url': 'data_series_url_fr',
    'data_dictionary': 'data_dictionary_fr', # note: different than english
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

def data_gc_ca_2012_choices(name):
    """
    Return a list of the choices from <name>.xml like:
    [{'data_gc_ca_2012_guid': ..., 'en': ..., 'fr': ... }, ...]
    """
    choices = []
    with open(os.path.join(DATA_GC_CA_2012, name + '.xml')) as c:
        croot = lxml.etree.parse(c)
        for node in croot.xpath('/root/item'):
            option = lang_versions(node, 'name')
            option['data_gc_ca_2012_guid'] = node.get('id')
            choices.append(option)
    return choices

def main():
    schema_out = {
        'sections_fields': [],
        }

    with open(SCHEMA_NAME) as s:
        root = lxml.etree.parse(s)
        schema_out['intro'] = lang_versions(root, '//intro')

        for section, fields in SECTIONS_FIELDS:
            new_section = {
                'name': {'en': section}, # FIXME: French version?
                'fields': [],
                }
            for field in fields:
                f = FIELD_MAPPING[field]
                xp = '//item[inputname="%s"]' % f
                new_field = {
                    'id': field,
                    'data_gc_ca_2012_id': f,
                    'name': lang_versions(root, xp + '/name'),
                    'help': lang_versions(root, xp + '/helpcontext'),
                    'type': "".join(root.xpath(xp +
                        '/type1/inputtype[1]/text()')),
                    }
                old_id_fr = BILINGUAL_FIELDS.get(field, None)
                if old_id_fr:
                    new_field['data_gc_ca_2012_id_fr'] = old_id_fr
                new_field['bilingual'] = bool(old_id_fr)

                if not new_field['type']:
                    # this seems to indicate a selection from a list
                    new_field['choices'] = data_gc_ca_2012_choices(f)
                    new_field['type'] = 'choice'

                new_section['fields'].append(new_field)
            schema_out['sections_fields'].append(new_section)

    return json.dumps(schema_out, sort_keys=True, indent=2)

print main()


