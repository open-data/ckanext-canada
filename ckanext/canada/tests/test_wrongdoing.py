# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('with_request_context')
class TestWrongdoing(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        org = Organization()
        lc = LocalCKAN()

        lc.action.recombinant_create(dataset_type='wrongdoing', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='wrongdoing', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('wrongdoing')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None
