# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resources

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{'dataset_type': 'service'}],
    indirect=True)
class TestService(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('service')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=request.config.cache.get("resource_id", None),
            records=[record])


    def test_blank(self, request):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[{}])
        assert ve is not None


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{
        'dataset_type': 'service',
        'resource_key': 1
    }],
    indirect=True)
class TestStdService(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('service-std')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=request.config.cache.get("resource_id", None),
            records=[record])


    def test_blank(self, request):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[{}])
        assert ve is not None


    def test_service_std_target(self, request):
        lc = LocalCKAN()
        resource_id = request.config.cache.get("resource_id", None)
        record = dict(
            get_chromo('service-std')['examples']['record'],
            service_std_target='0.99999')
        lc.action.datastore_upsert(
            resource_id=resource_id,
            records=[record])
        assert lc.action.datastore_search(resource_id=resource_id)['records'][0]['service_std_target'] == 0.99999
        record['service_std_target'] = 0.5
        lc.action.datastore_upsert(
            resource_id=resource_id,
            records=[record])
        assert lc.action.datastore_search(resource_id=resource_id)['records'][0]['service_std_target'] == 0.5
        record['service_std_target'] = None
        lc.action.datastore_upsert(
            resource_id=resource_id,
            records=[record])
        assert lc.action.datastore_search(resource_id=resource_id)['records'][0]['service_std_target'] == None
        record['service_std_target'] = -0.01
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=resource_id,
                records=[record])
        assert ve is not None
        record['service_std_target'] = 1.01
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=resource_id,
                records=[record])
        assert ve is not None
