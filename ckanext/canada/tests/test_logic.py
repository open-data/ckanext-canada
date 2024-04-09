# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN

from ckanext.canada.tests.factories import CanadaResource as Resource


class TestCanadaLogic(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestCanadaLogic, self).setup_method(method)

        self.lc = LocalCKAN()

    def test_data_dictionary(self):
        """
        The custom fields should get saved in the Data Dictionary,
        and be returned from datastore_info.
        """
        resource = Resource()
        self.lc.action.datastore_create(resource_id=resource['id'],
                                        force=True,
                                        fields=[{'id': 'exampled_id',
                                                 'type': 'text',
                                                 'info': {'label_en': 'Example Label',
                                                          'label_fr': 'Example Label FR',
                                                          'notes_en': 'Example Description',
                                                          'notes_fr': 'Example Description FR'}}])

        ds_info = self.lc.action.datastore_info(id=resource['id'])

        assert 'fields' in ds_info
        assert len(ds_info['fields']) == 1
        assert ds_info['fields'][0]['id'] == 'exampled_id'
        assert 'info' in ds_info['fields'][0]
        assert 'label_en' in ds_info['fields'][0]['info']
        assert 'label_fr' in ds_info['fields'][0]['info']
        assert 'notes_en' in ds_info['fields'][0]['info']
        assert 'notes_fr' in ds_info['fields'][0]['info']

