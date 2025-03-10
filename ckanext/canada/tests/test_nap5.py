# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestNap5(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestNap5, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='nap5', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='nap5', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('nap5')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err, err

    def test_required(self):
        record = dict(
            get_chromo('nap5')['examples']['record'],
            commitments='',
            milestones='',
            status='',
            progress_en='',
            progress_fr='',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'commitments': ['This field must not be empty'],
            'milestones': ['This field must not be empty'],
            'status': ['This field must not be empty'],
            'progress_en': ['This field must not be empty'],
            'progress_fr': ['This field must not be empty'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]
