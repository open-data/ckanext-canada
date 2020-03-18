# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import Organization

from ckanext.recombinant.tables import get_chromo

class TestHospitalityQ(FunctionalTestBase):
    def setup(self):
        super(TestHospitalityQ, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('hospitalityq')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])


class TestHospitalityQNil(FunctionalTestBase):
    def setup(self):
        super(TestHospitalityQNil, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])
        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('hospitalityq-nil')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
                      lc.action.datastore_upsert,
                      resource_id=self.resource_id,
                      records=[{}])
