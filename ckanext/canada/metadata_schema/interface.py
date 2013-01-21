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

    The ordered list of dataset fields available as::

        schema_description.dataset_fields

    Fields are dicts with keys such as 'id', 'name', 'help', etc.
    The ordered list of sections are available as::

        schema_description.dataset_sections

    Sections are dicts with keys including 'name' and 'fields'.

    The ordered list of resource fields are available as::

        schema_description.resource_fields
    """
    def __init__(self):
        with open(_JSON_NAME) as j:
            schema = json.load(j)

        self.intro = schema['intro']
        self.languages = schema['languages']
        self.dataset_sections = schema['dataset_sections']
        self.dataset_fields = []
        for s in self.dataset_sections:
            self.dataset_fields.extend(s['fields'])
        self.resource_fields = schema['resource_fields']

    def dataset_fields_by_ckan_id(self, include_existing=True, section=None):
        """
        Generate (field_name, language, field) tuples for filling
        in CKAN field information.

        language will be None for fields only in a single language
        """
        fields = section['fields'] if section else self.dataset_fields
        return self._fields_by_ckan_id(fields, include_existing)

    def resource_fields_by_ckan_id(self, include_existing=True):
        """
        Generate (field_name, language, field) tuples for filling
        in CKAN resource field information.
        """
        return self._fields_by_ckan_id(self.resource_fields, include_existing)

    def _fields_by_ckan_id(self, fields, include_existing):
        "helper for *_fields_by_ckan_id"
        for f in fields:
            if include_existing or not f['existing']:
                yield (f['id'],
                    self.languages[0] if f['bilingual'] else None,
                    f)
            if f['bilingual']:
                yield ("%s_%s" % (f['id'], self.languages[1]),
                    self.languages[1],
                    f)


# FIXME: remove these
for old, new in [('sections', 'dataset_sections'),
        ('fields', 'dataset_fields'),
        ('fields_by_ckan_id', 'dataset_fields_by_ckan_id')]:
    def nope(self, old=old, new=new):
        assert 0, '%s was renamed to %s' % (old, new)
    setattr(MetadataSchema, old, property(nope))


