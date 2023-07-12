# -*- coding: UTF-8 -*-
from nose.tools import assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.canada.tests import canada_tests_init_validation


class TestAti(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestAti, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='ati', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='ati', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('ati')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])


class TestAtiNil(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestAtiNil, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='ati', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='ati', owner_org=org['name'])
        self.resource_id = rval['resources'][1]['id']


    def test_example(self):
        record = get_chromo('ati-nil')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
                      self.lc.action.datastore_upsert,
                      resource_id=self.resource_id,
                      records=[{}])

