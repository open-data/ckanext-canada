# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resource

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{'dataset_type': 'contractsa'}],
    indirect=True)
class TestContractsA(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('contractsa')['examples']['record']
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


    def test_year(self, request):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contractsa')['examples']['record'],
            year='2050')
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'year': [
                'This must list the year you are reporting on (not the fiscal year).'],
        }
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]
