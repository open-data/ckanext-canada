# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.canada.tests import canada_tests_init_validation


class TestService(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestService, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])
        self.service_id = rval['resources'][0]['id']
        self.service_std_id = rval['resources'][1]['id']


    def test_example(self):
        record = get_chromo('service')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.service_id,
            records=[record])
        record = get_chromo('service-std')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.service_id,
            records=[{}])
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[{}])


    def test_service_std_target(self):
        record = dict(
            get_chromo('service-std')['examples']['record'],
            service_std_target='0.99999')
        self.lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            self.lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            0.99999)
        record['service_std_target'] = 0.5
        self.lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            self.lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            0.5)
        record['service_std_target'] = None
        self.lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            self.lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            None)
        record['service_std_target'] = -0.01
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[record])
        record['service_std_target'] = 1.01
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[record])

