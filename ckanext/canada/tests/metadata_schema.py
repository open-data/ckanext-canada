import unittest

from ckanext.canada.metadata_schema import schema_description

class TestSchemaDescription(unittest.TestCase):
    def setUp(self):
        self.sd = schema_description

    def test_schema_has_data(self):
        self.assertGreater(len(self.sd.dataset_sections), 3)
        self.assertGreater(len(self.sd.dataset_fields), 10)
        self.assertGreater(len(self.sd.resource_fields), 3)
        for f in self.sd.dataset_sections:
            self.assertGreater(len(f['fields']), 0)

    # FIXME: remove this
    def test_old_attribute_names(self):
        with self.assertRaises(AssertionError):
            self.sd.fields
        with self.assertRaises(AssertionError):
            self.sd.fields_by_ckan_id
        with self.assertRaises(AssertionError):
            self.sd.sections
