# -*- coding: UTF-8 -*-
import sys
import os
from importlib import util
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

filter_consultations_path = os.path.join(os.path.dirname(str(__file__)), '../../../bin/filter/filter_consultations.py')
spec = util.spec_from_file_location("canada.bin.filters.consultations", filter_consultations_path)
filter_consultations = util.module_from_spec(spec)
sys.modules["canada.bin.filters.consultations"] = filter_consultations
spec.loader.exec_module(filter_consultations)


class TestConsultations(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestConsultations, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='consultations', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='consultations', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('consultations')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('consultations')['examples']['record'].copy()
        record['registration_number'] = 'this,is,a,failure'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'registration_number' in err['records'][0]
        assert err['records'][0]['registration_number'] == ['Comma is not allowed in Registration Number field']

    def test_blank(self):
        """
        Should raise a Database key error
        """
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'registration_number' in err['key'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception
        """
        chromo = get_chromo('consultations')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['publishable', 'title_en', 'title_fr',
                                    'start_date', 'end_date',
                                    'profile_page_en', 'profile_page_fr',
                                    'high_profile',
                                    ]

        for field in chromo['fields']:
            if field['datastore_id'] in chromo['datastore_primary_key']:
                continue
            if field.get('excel_required') or field.get('form_required'):
                assert field['datastore_id'] in expected_required_fields
                record[field['datastore_id']] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_conditional_required_fields(self):
        """
        Excluding conditional required fields should raise an exception
        """
        chromo = get_chromo('consultations')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['subjects', 'description_en', 'description_fr',
                                    'target_participants_and_audience', ]

        for field in chromo['fields']:
            if field['datastore_id'] in chromo['datastore_primary_key']:
                continue
            if field['datastore_id'] == 'end_date':
                continue
            if field.get('excel_required') or field.get('form_required'):
                assert field['datastore_id'] in expected_required_fields
                record[field['datastore_id']] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('consultations')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['publishable', 'partner_departments', 'subjects',
                                  'target_participants_and_audience', 'status',
                                  'report_available_online', 'high_profile', 'rationale', ]

        for field in chromo['fields']:
            if field.get('published_resource_computed_field'):
                continue
            if 'choices_file' in field or 'choices' in field:
                assert field['datastore_id'] in expected_choice_fields
                if field['datastore_type'] == '_text':
                    record[field['datastore_id']] = ['zzz']
                else:
                    record[field['datastore_id']] = 'zzz'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for expected_choice_field in expected_choice_fields:
            assert expected_choice_field in err['records'][0]

    def test_multiple_errors(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'registration_number': 'CCC0250_new_records',
                    'publishable': 'Q',
                    'subjects': ["IP", "CD", "HS", "GEO", "SE", "MATH"],
                    'title_fr': 'seulment français',
                    'description_en': 'only english',
                    'target_participants_and_audience': ["ZOMBIES", "IP", "IG", "PT"],
                    'end_date': "2018-05-15",
                    'status': 'P',
                    'profile_page_en': 'http://example.gc.ca/en',
                    'profile_page_fr': 'http://example.gc.ca/fr',
                    'partner_departments': ["D271", "DARN", "D141"],
                    'policy_program_lead_email': 'program.lead@example.gc.ca',
                    'high_profile': "Y",
                    'report_available_online': "N",
                    }])
        model.Session.rollback()
        err = ve.value.error_dict['records'][0]
        expected = {
            'publishable': ['Invalid choice: "Q"'],
            'subjects': ['Invalid choice: "GEO,MATH"'],
            'title_en': ['This field must not be empty'],
            'description_fr': ['This field must not be empty'],
            'target_participants_and_audience': ['Invalid choice: "ZOMBIES"'],
            'start_date': ['This field must not be empty'],
            'partner_departments': ['Invalid choice: "DARN"'],
            'rationale': ['This field must not be empty'],
        }
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]

    def test_not_going_forward_unpublished(self):
        record = get_chromo('consultations')['examples']['record']
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[dict(record, publishable='Y', status='NF')])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'status' in err['records'][0]

    def test_filter_script(self):
        """
        Filter out default Registry fields.

        NOTE: csv.DictReader treats every dict value as a string,
              so we need to use Strings here. Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        record = get_chromo('consultations')['examples']['record'].copy()

        # filters out publishable, record_created, record_modified, user_modified
        record['publishable'] = 'Y'
        record['record_created'] = 'Not Blank'
        record['record_modified'] = 'Not Blank'
        record['user_modified'] = 'Not Blank'

        test_record = filter_consultations.test(dict(record))
        assert 'publishable' not in test_record
        assert 'record_created' not in test_record
        assert 'record_modified' not in test_record
        assert 'user_modified' not in test_record
