# -*- coding: UTF-8 -*-
from nose.tools import assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.canada.tests import canada_tests_init_validation


class TestGrants(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestGrants, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='grants', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='grants', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('grants')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])


    def test_empty_string_instead_of_null(self):
        record = dict(get_chromo('grants')['examples']['record'])
        record['foreign_currency_type'] = ''
        record['foreign_currency_value'] = ''
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

