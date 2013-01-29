import unittest

from ckanext.canada.metadata_schema import schema_description

class TestSchemaDescription(unittest.TestCase):
    def setUp(self):
        self.sd = schema_description

    def test_schema_has_data(self):
        self.assertTrue(len(self.sd.dataset_sections) > 2)
        self.assertTrue(len(self.sd.dataset_fields) > 10)
        self.assertTrue(len(self.sd.resource_fields) > 3)
        for f in self.sd.dataset_sections:
            self.assertTrue(len(f['fields']) > 0)

    # FIXME: remove this
    def test_old_attribute_names(self):
        with self.assertRaises(AssertionError):
            self.sd.fields
        with self.assertRaises(AssertionError):
            self.sd.fields_by_ckan_id
        with self.assertRaises(AssertionError):
            self.sd.sections

    def test_fields_by_ckan_id(self):
        dataset_fields = list(self.sd.dataset_fields_by_ckan_id())
        self.assertTrue(len(dataset_fields) > 10)

        resource_fields = list(self.sd.resource_fields_by_ckan_id())
        self.assertTrue(len(resource_fields) > 3)

        self.assertEquals(len(dataset_fields),
            sum(len(list(self.sd.dataset_fields_by_ckan_id(section=s)))
                for s in self.sd.dataset_sections))

        extra_dataset_fields = list(self.sd.dataset_fields_by_ckan_id(False))
        self.assertTrue(len(dataset_fields) > len(extra_dataset_fields))

    def test_choices_by_pilot_uuid(self):
        fields_with_choices = [
            f for f in self.sd.dataset_fields if 'choices' in f]
        self.assertTrue(len(fields_with_choices) > 2)
        for f in fields_with_choices:
            a_choice = f['choices'][0]
            self.assertTrue(
                f['choices_by_pilot_uuid'][a_choice['pilot_uuid']] == a_choice)
