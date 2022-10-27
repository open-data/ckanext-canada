# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import Canada_Organization as Organization

from ckanext.recombinant.tables import get_chromo

class TestTravelQ(FunctionalTestBase):
    def setup(self):
        super(TestTravelQ, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='nap', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='nap', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('nap')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

    def test_milestones_depends_on_commitments(self):
        lc = LocalCKAN()
        record = get_chromo('nap')['examples']['record']
        record['commitments'] = 'C02'
        record['milestones'] = 'C02.1'
        record['indicators'] = 'C02.1.1'
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        record['commitments'] = 'C01'
        record['milestones'] = 'C02.1'
        record['indicators'] = 'C02.1.1'
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[record])

    def test_indicators_depends_on_milestones(self):
        lc = LocalCKAN()
        record = get_chromo('nap')['examples']['record']
        record['commitments'] = 'C01'
        record['milestones'] = 'C01.1'
        record['indicators'] = 'C01.1.1'
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        record['commitments'] = 'C01'
        record['milestones'] = 'C01.1'
        record['indicators'] = 'C02.1.1'
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[record])
