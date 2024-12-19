# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestContractsA(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestContractsA, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='contractsa', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='contractsa', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('contractsa')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'year' in err['key'][0]

    def test_year(self):
        record = dict(
            get_chromo('contractsa')['examples']['record'],
            year='2050')
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'year' in err['records'][0]
