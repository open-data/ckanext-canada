# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestAIStrategy(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestAIStrategy, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='aistrategy', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='aistrategy', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('aistrategy')['examples']['record']
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
        assert 'key' in err, err

    def test_required(self):
        record = dict(
            get_chromo('aistrategy')['examples']['record'],
            ref_number='',
            reporting_period='',
            priority_area='',
            key_action='',
            sub_action='',
            activity='',
            expected_completion='',
            lead_department='',
            status='',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict['records'][0]
        expected = {
            'ref_number': ['This field must not be empty'],
            'reporting_period': ['This field must not be empty'],
            'priority_area': ['This field must not be empty'],
            'key_action': ['This field must not be empty'],
            'sub_action': ['This field must not be empty'],
            'activity': ['This field must not be empty'],
            'expected_completion': ['This field must not be empty'],
            'lead_department': ['This field must not be empty'],
            'status': ['This field must not be empty'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]

    def test_max_chars(self):
        """
        Over max character field values should raise an exception
        """
        chromo = get_chromo('aistrategy')
        record = chromo['examples']['record'].copy()

        expect_maxchar_fields = ['description_en', 'description_fr',
                                 'progress_en', 'progress_fr']

        for field in chromo['fields']:
            if field.get('max_chars'):
                assert field['datastore_id'] in expect_maxchar_fields
                record[field['datastore_id']] = 'xx' * field.get('max_chars')

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for maxchar_field in expect_maxchar_fields:
            assert maxchar_field in err['records'][0]
