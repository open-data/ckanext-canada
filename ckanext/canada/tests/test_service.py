# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('with_request_context')
class TestService(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('service')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None


@pytest.mark.usefixtures('with_request_context')
class TestStdService(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']


    def test_example(self):
        record = get_chromo('service-std')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None


    def test_service_std_target(self):
        record = dict(
            get_chromo('service-std')['examples']['record'],
            service_std_target='0.99999')
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
        assert self.lc.action.datastore_search(resource_id=self.resource_id)['records'][0]['service_std_target'] == 0.99999
        record['service_std_target'] = 0.5
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
        assert self.lc.action.datastore_search(resource_id=self.resource_id)['records'][0]['service_std_target'] == 0.5
        record['service_std_target'] = None
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
        assert self.lc.action.datastore_search(resource_id=self.resource_id)['records'][0]['service_std_target'] == None
        record['service_std_target'] = -0.01
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None
        record['service_std_target'] = 1.01
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None
