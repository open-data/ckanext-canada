# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resource

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{'dataset_type': 'reclassification'}],
    indirect=True)
class TestReclassification(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('reclassification')['examples']['record']
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
        'dataset_type': 'reclassification',
        'resource_key': 1,
    }],
    indirect=True)
class TestReclassificationNil(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('reclassification-nil')['examples']['record']
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
