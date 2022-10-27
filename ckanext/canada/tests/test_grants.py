# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import Canada_Organization as Organization

from ckanext.recombinant.tables import get_chromo

class TestGrants(FunctionalTestBase):
    def setup(self):
        super(TestGrants, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='grants', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='grants', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('grants')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

    def test_empty_string_instead_of_null(self):
        lc = LocalCKAN()
        record = dict(get_chromo('grants')['examples']['record'])
        record['foreign_currency_type'] = ''
        record['foreign_currency_value'] = ''
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
