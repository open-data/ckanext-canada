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


filter_generic_path = os.path.join(os.path.dirname(str(__file__)), '../../../bin/filter/filter_modified_created.py')
spec = util.spec_from_file_location("canada.bin.filters.generic", filter_generic_path)
filter_generic = util.module_from_spec(spec)
sys.modules["canada.bin.filters.generic"] = filter_generic
spec.loader.exec_module(filter_generic)


class TestHospitalityQ(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestHospitalityQ, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('hospitalityq')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('hospitalityq')['examples']['record'].copy()
        record['ref_number'] = 'this,is,a,failure'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'ref_number' in err['records'][0]
        assert err['records'][0]['ref_number'] == ['Comma is not allowed in Reference Number field']

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
        assert 'ref_number' in err['key'][0]

    def test_start_date_required(self):
        """
        Should raise an exaception if missing start_date
        """
        record = get_chromo('hospitalityq')['examples']['record'].copy()
        record['start_date'] = None
        with pytest.raises(ValidationError):
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record]
            )
        model.Session.rollback()

    def test_conditional_required_fields(self):
        """
        Excluding conditional required fields should raise an exception
        """
        chromo = get_chromo('hospitalityq')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['title_en', 'title_fr', 'name',
                                    'description_en', 'description_fr',
                                    'end_date',
                                    'location_en', 'location_fr',
                                    'vendor_en', 'vendor_fr',
                                    'employee_attendees', 'guest_attendees',
                                    'total', ]

        for field in chromo['fields']:
            if field['datastore_id'] in chromo['datastore_primary_key']:
                continue
            if field['datastore_id'] == 'start_date':
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
        chromo = get_chromo('hospitalityq')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['disclosure_group',]

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

    def test_dates(self):
        """
        Start Date cannot be in the future, and dates must be chronological
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2999999-01-29'
        record['end_date'] = '2999999-01-30'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'start_date' in err
            assert 'end_date' in err
        model.Session.rollback()
        record['start_date'] = '2024-01-29'
        record['end_date'] = '2024-01-15'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'start_date' in err
        model.Session.rollback()

    def test_attendees(self):
        """
        Attendee fields cannot be zero or below if on or after April 1st 2025
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2025-04-29'
        record['end_date'] = '2025-04-30'
        record['employee_attendees'] = -2
        record['guest_attendees'] = -5
        record['employee_attendees'] = 0

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'employee_attendees' in err
            assert 'guest_attendees' in err
            assert 'employee_attendees' in err
        model.Session.rollback()
        record['start_date'] = '2024-04-29'
        record['end_date'] = '2024-04-30'

        self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

    def test_disclosure_group(self):
        """
        Disclosure Group is required if on or after April 1st 2025
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2025-04-21'
        record['end_date'] = '2025-04-24'
        record['disclosure_group'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'disclosure_group' in err
        model.Session.rollback()
        record['start_date'] = '2024-04-21'
        record['end_date'] = '2024-04-24'
        record['disclosure_group'] = 'SLE'

        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_vendor_format(self):
        record = get_chromo('hospitalityq')['examples']['record']
        record['start_date'] = '2024-04-21'
        record['end_date'] = '2024-04-24'

        # tests some incorrect formats
        incorrect_formats = [
            'Starbucks ;',
            'Tim Hortons & Starbucks ;   ',
            'Les Impertinentes ; ; Les Street Monkeys',
            'Starbucks, Montanas ; ',
        ]
        for incorrect_format in incorrect_formats:
            record['vendor_other_en'] = incorrect_format
            record['vendor_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            model.Session.rollback()
            err = ve.value.error_dict['records'][0]
            expected = {
                'vendor_other_en': ["Invalid format for multiple commercial establishments or vendors. Use <Vendor Name>;<Vendor 2 Name> (e.g. Les Impertinentes;Les Street Monkeys)"],
                'vendor_other_fr': ["Invalid format for multiple commercial establishments or vendors. Use <Vendor Name>;<Vendor 2 Name> (e.g. Les Impertinentes;Les Street Monkeys)"],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert k in expected
                assert err[k] == expected[k]

        # test surrounding white space stripping
        raw_values_expected_values = {
            ' Les Impertinentes ; Les Street Monkeys ': 'Les Impertinentes;Les Street Monkeys',
            'Les Impertinentes ; Les Street Monkeys ;  Starbucks ': 'Les Impertinentes;Les Street Monkeys;Starbucks',
            '  Les Impertinentes  ;  Les Street Monkeys  ;  Tim Hortons  ': 'Les Impertinentes;Les Street Monkeys;Tim Hortons',
            '  Les Impertinentes  ': 'Les Impertinentes',
        }
        for raw_value, excpected_value in raw_values_expected_values.items():
            record['vendor_other_en'] = raw_value
            record['vendor_other_fr'] = raw_value
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            result = self.lc.action.datastore_search(resource_id=self.resource_id)
            records = result.get('records')
            assert len(records) > 0
            assert records[0]['vendor_other_en'] == excpected_value
            assert records[0]['vendor_other_fr'] == excpected_value

    def test_filter_script(self):
        """
        Filter out default Registry fields.

        NOTE: csv.DictReader treats every dict value as a string,
              so we need to use Strings here. Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        record = get_chromo('hospitalityq')['examples']['record'].copy()

        # filters out record_created, record_modified, user_modified
        record['record_created'] = 'Not Blank'
        record['record_modified'] = 'Not Blank'
        record['user_modified'] = 'Not Blank'

        test_record = filter_generic.test(dict(record))
        assert 'record_created' not in test_record
        assert 'record_modified' not in test_record
        assert 'user_modified' not in test_record


class TestHospitalityQNil(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestHospitalityQNil, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('hospitalityq-nil')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

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
        assert 'year, month' in err['key'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('hospitalityq-nil')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['month',]

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

    def test_date_constraints(self):
        """
        Should not be able to input unsupported years and months
        """
        record = get_chromo('hospitalityq-nil')['examples']['record'].copy()

        # cannot be after current year
        record['year'] = 2999
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'year' in err['records'][0]
        assert err['records'][0]['year'] == ['This must list the year you are reporting on (not the fiscal year).']
