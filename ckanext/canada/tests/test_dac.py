# -*- coding: UTF-8 -*-
from nose.tools import assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.helpers import recombinant_choice_fields


class TestDAC(FunctionalTestBase):
    def setup(self):
        super(TestDAC, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='dac', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='dac', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('dac')['examples']['record']
        choices_fields = recombinant_choice_fields('dac')
        for f in choices_fields:
            if f['datastore_id'] != 'member_name':
                continue
            record['member_name'] = f['choices'][0][0]
            break
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

