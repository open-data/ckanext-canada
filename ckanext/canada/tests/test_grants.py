# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resources

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{'dataset_type': 'grants'}],
    indirect=True)
class TestGrants(object):
    def test_example(self,request):
        lc = LocalCKAN()
        record = get_chromo('grants')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=request.config.cache.get("resource_id", None),
            records=[record])


    def test_blank(self, request):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None


    def test_empty_string_instead_of_null(self, request):
        lc = LocalCKAN()
        record = dict(get_chromo('grants')['examples']['record'])
        record['foreign_currency_type'] = ''
        record['foreign_currency_value'] = ''
        lc.action.datastore_upsert(
            resource_id=request.config.cache.get("resource_id", None),
            records=[record])
