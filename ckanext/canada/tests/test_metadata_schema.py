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

    def test_field_iter(self):
        dataset_fields = list(self.sd.dataset_field_iter())
        self.assertTrue(len(dataset_fields) > 10)

        resource_fields = list(self.sd.resource_field_iter())
        self.assertTrue(len(resource_fields) > 3)

        self.assertEquals(len(dataset_fields),
            sum(len(list(self.sd.dataset_field_iter(section=s)))
                for s in self.sd.dataset_sections))

        extra_dataset_fields = list(self.sd.dataset_field_iter(False))
        self.assertTrue(len(dataset_fields) > len(extra_dataset_fields))

    def test_choices_by_pilot_uuid(self):
        fields_with_choices = [
            f for f in self.sd.dataset_fields if 'choices' in f]
        self.assertTrue(len(fields_with_choices) > 2)
        for f in fields_with_choices:
            if not f['choices_by_pilot_uuid']:
                continue
            uuid, a_choice = f['choices_by_pilot_uuid'].items()[0]
            self.assertTrue(a_choice['pilot_uuid'] == uuid)
