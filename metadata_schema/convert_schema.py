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

schema_out = {
    'sections_fields': [],
    }

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

# '2012 field name': 'new field name'
FIELD_MAPPING = {
    'owner': 'author_email', # existing, was 'Contact'
    'contact_name': 'individual_name',
    'contact_title': 'position_name',
    'contact_phone': 'telephone_number_voice',
    'contact_email': 'maintainer_email', # existing, was 'Email'
    'title_en': 'title', # existing
    'department': 'organization_name',
    'category': 'thesaurus',
    'language__': 'language',
    'date_released': 'date',
    'date_update': 'date_modified',
    'frequency': 'maintenance_and_update_frequency',
    'description_en': 'info', # existing, was 'Abstract'
    'keywords_en': 'tags', # existing, was 'Keywords'
    'program_page_en': 'program_url',
    'data_series_url_en': 'url', # existing, was 'Data Series URL'
    'dictionary_list:_en': 'data_dictionary',
    'supplementary_documentation_en': 'supplemental_information_other',
    'Geographic_Region_Name': 'geographic_region_name',
    'time_period_start': 'begin_position',
    'time_period_end': 'end_position',
    'group_name_en': 'data_series_name',
# XXX doesn't seem right: 'number_datasets': 'issue_identification',
    }


# '2012 French field name' : 'new corresponding english field name'
BILINGUAL_FIELDS = {
    'title_fr': 'title',
    'description_fr': 'info',
    'keywords_fr': 'tags',
    'program_url_fr': 'program_url', # note: different than english
    'data_series_url_fr': 'url',
    'data_dictionary_fr': 'data_dictionary', # note: different than english
    'supplementary_documentation_fr': 'supplemental_information_other',
    'group_name_fr': 'data_series_name',
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
    reverse_field_mapping = {v:k for k, v in FIELD_MAPPING.items()}
    reverse_bilingual_fields = {v:k for k, v in BILINGUAL_FIELDS.items()}


    with open(SCHEMA_NAME) as s:
        root = lxml.etree.parse(s)
        schema_out['intro'] = lang_versions(root, '//intro')

        for section, fields in SECTIONS_FIELDS:
            new_section = {
                'name': {'en': section}, # FIXME: French version?
                'fields': [],
                }
            for field in fields:
                f = reverse_field_mapping[field]
                xp = '//item[inputname="%s"]' % f
                new_field = {
                    'id': field,
                    'data_gc_ca_2012_id': f,
                    'name': lang_versions(root, xp + '/name'),
                    'help': lang_versions(root, xp + '/helpcontext'),
                    'type': "".join(root.xpath(xp +
                        '/type1/inputtype[1]/text()')),
                    }
                old_id_fr = reverse_bilingual_fields.get(field, None)
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


