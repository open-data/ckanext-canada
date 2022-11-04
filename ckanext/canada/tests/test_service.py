# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

@pytest.mark.usefixtures('clean_db')
class TestService(object):
    def __init__(self):
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])
        self.service_id = rval['resources'][0]['id']
        self.service_std_id = rval['resources'][1]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('service')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.service_id,
            records=[record])
        record = get_chromo('service-std')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.service_id,
            records=[{}])
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[{}])

    def test_service_std_target(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('service-std')['examples']['record'],
            service_std_target='0.99999')
        lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            0.99999)
        record['service_std_target'] = 0.5
        lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            0.5)
        record['service_std_target'] = None
        lc.action.datastore_upsert(
            resource_id=self.service_std_id,
            records=[record])
        assert_equal(
            lc.action.datastore_search(resource_id=self.service_std_id)
                ['records'][0]['service_std_target'],
            None)
        record['service_std_target'] = -0.01
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[record])
        record['service_std_target'] = 1.01
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.service_std_id,
            records=[record])
