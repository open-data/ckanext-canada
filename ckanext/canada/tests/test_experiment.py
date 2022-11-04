# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

@pytest.mark.usefixtures('clean_db')
class TestExperiment(object):
    def __init__(self):
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='experiment', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='experiment', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('experiment')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

