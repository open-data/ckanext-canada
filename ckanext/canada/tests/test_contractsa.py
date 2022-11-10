# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestContractsA(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        org = Organization()
        lc = LocalCKAN()

        lc.action.recombinant_create(dataset_type='contractsa', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='contractsa', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('contractsa')['examples']['record']
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


    def test_year(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contractsa')['examples']['record'],
            year='2050')
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'year': [
                'This must list the year you are reporting on (not the fiscal year).'],
        }
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]
