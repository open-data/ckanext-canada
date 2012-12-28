import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_JSON_NAME = os.path.join(_HERE, 'schema.json')

class MetadataSchema(object):
    """
    The internal interface for accessing data stored in 'schema.json'.

    This API shouldn't change even if the format of the json itself
    changes.  Use this in your code::

        from ckanext.canada.metadata_schema import schema_description

    The ordered list of fields available as::

        schema_description.fields

    Fields are dicts with keys such as 'id', 'name', 'help', etc.
    The ordered list of sections are available as::

        schema_description.sections

    Sections are dicts with keys including 'name' and 'fields'.

    A 'language_field_names' is added to the fields containing a list
    of the CKAN form field names for all languages for this field.
    """
    def __init__(self):
        with open(_JSON_NAME) as j:
            schema = json.load(j)

        self.intro = schema['intro']
        self.languages = schema['languages']
        self.sections = schema['sections_fields']
        self.fields = []
        for s in self.sections:
            self.fields.extend(s['fields'])

        for f in self.fields:
            f['language_field_names'] = [f['id']]
            if f['bilingual']:
                f['language_field_names'].append("%s_%s" % (
                    f['id'], self.languages[1]))
