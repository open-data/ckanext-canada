import unittest

from ckanext.canada.metadata_schema import schema_description

class TestSchemaDescription(unittest.TestCase):
    def setUp(self):
        self.sd = schema_description

    def test_old_attribute_names(self):
        with self.assertRaises(AssertionError):
            self.sd.fields
        with self.assertRaises(AssertionError):
            self.sd.fields_by_ckan_id
        with self.assertRaises(AssertionError):
            self.sd.sections
