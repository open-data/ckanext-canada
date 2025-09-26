# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.helpers import recombinant_choice_fields


class TestDAC(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestDAC, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='dac', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='dac', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('dac')['examples']['record']
        choices_fields = recombinant_choice_fields('dac')
        record['member_name'] = choices_fields['member_name'][0][0]
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'reporting_period, line_number' in err['key'][0]
