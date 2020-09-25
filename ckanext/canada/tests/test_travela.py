# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import Organization

from ckanext.recombinant.tables import get_chromo

class TestTravelA(FunctionalTestBase):
    def setup(self):
        super(TestTravelA, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='travela', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='travela', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('travela')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

    def test_year(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('travela')['examples']['record'],
            year='2050')
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'year': [
                'This must list the year you are reporting on (not the fiscal year).'],
        }
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))