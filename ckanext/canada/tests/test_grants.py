# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestGrants(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestGrants, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='grants', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='grants', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('grants')['examples']['record']
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
        assert 'ref_number, amendment_number' in err['key'][0]

    def test_empty_string_instead_of_null(self):
        record = dict(get_chromo('grants')['examples']['record'])
        record['foreign_currency_type'] = ''
        record['foreign_currency_value'] = ''
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
