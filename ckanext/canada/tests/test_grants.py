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
        """
        Example data should load
        """
        record = get_chromo('grants')['examples']['record'].copy()
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
        assert 'ref_number, amendment_number' in err['key'][0]

    def test_empty_string_instead_of_null(self):
        record = dict(get_chromo('grants')['examples']['record'])
        record['foreign_currency_type'] = ''
        record['foreign_currency_value'] = ''
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('grants')['examples']['record'].copy()
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

    def test_agreement_value(self):
        """
        Must be greater than or equal to 0

        NOTE: conditional on `agreement_start_date`>=2026-05-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2026-05-01'
        record['agreement_end_date'] = '2026-08-30'
        record['amendment_number'] = 0

        bad_formats = [
            -200,
            -0.01,
        ]

        for bad_format in bad_formats:
            record['agreement_value'] = bad_format

            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            model.Session.rollback()
            err = ve.value.error_dict
            assert 'records' in err
            assert 'agreement_value' in err['records'][0]

        good_formats = [
            200,
            1,
            0,
            0.01,
            0.99,
            0.009,  # rounds to 0.01
            0.001,  # rounds to 0
        ]

        for good_format in good_formats:
            record['agreement_value'] = good_format

            self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])

    def test_business_number_format(self):
        """
        Should be a 9 digit natural number

        NOTE: conditional on `agreement_start_date`>=2025-12-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2025-12-01'
        record['amendment_number'] = 0

        bad_formats = [
            'this is no good',
            '80',
            '2,000',
            '-1800',
            '2600-',
            '29.50',
            '00087',
            '58928100487832',
        ]

        for bad_format in bad_formats:
            record['recipient_business_number'] = bad_format

            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            model.Session.rollback()
            err = ve.value.error_dict
            assert 'records' in err
            assert 'recipient_business_number' in err['records'][0]

        record['recipient_business_number'] = '500010009'

        self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

    def test_riding_number_format(self):
        """
        Should be a 5 digit natural number

        NOTE: conditional on `agreement_start_date`>=2025-12-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2025-12-01'
        record['amendment_number'] = 0

        bad_formats = [
            'this is no good',
            '80',
            '2,000',
            '-1800',
            '2600-',
            '29.50',
            '00087',
            '58928100487832',
        ]

        for bad_format in bad_formats:
            record['federal_riding_number'] = bad_format

            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            model.Session.rollback()
            err = ve.value.error_dict
            assert 'records' in err
            assert 'federal_riding_number' in err['records'][0]

        record['federal_riding_number'] = '50001'

        self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

    def test_postal_code_format(self):
        """
        Should enforce Canadian postal code format

        NOTE: conditional on `agreement_start_date`>=2025-12-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2025-12-01'
        record['amendment_number'] = 0

        bad_formats = [
            'this is no good',
            '15267',
            'A1B2C3'
        ]

        for bad_format in bad_formats:
            record['recipient_postal_code'] = bad_format

            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            model.Session.rollback()
            err = ve.value.error_dict
            assert 'records' in err
            assert 'recipient_postal_code' in err['records'][0]

        record['recipient_postal_code'] = 'A1B 2C3'

        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_dates(self):
        """
        Start Date cannot be in the future, and dates must be chronological

        NOTE: conditional on `agreement_start_date`>=2025-12-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2025-12-05'
        record['amendment_number'] = 0
        record['agreement_end_date'] = '2025-12-01'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'agreement_start_date' in err['records'][0]

        record['agreement_start_date'] = '2099-01-01'
        record['amendment_number'] = 0
        # Disable temporarily for OPEN-4393
        # record['agreement_end_date'] = '2099-01-02'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'agreement_start_date' in err['records'][0]

    def test_amendment_fields(self):
        """
        Having an amendment_number other than 0 should require amendment_date
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2018-04-01'
        record['amendment_number'] = 5
        record['amendment_date'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'amendment_date' in err['records'][0]

    def test_foreign_currency_fields(self):
        """
        Excluding either of the foreign_currency fields should require the other
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2018-04-01'
        record['amendment_number'] = 0

        record['foreign_currency_type'] = None
        record['foreign_currency_value'] = "450000"

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'foreign_currency_type' in err['records'][0]

        record['foreign_currency_type'] = "USD"
        record['foreign_currency_value'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'foreign_currency_value' in err['records'][0]

    def test_province_required_field(self):
        """
        Having recipient_city as CA should require recipient_province

        NOTE: conditional on `agreement_start_date`>=2018-04-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2018-04-01'
        record['amendment_number'] = 0
        record['recipient_country'] = 'CA'

        record['recipient_province'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'recipient_province' in err['records'][0]

    def test_required_fields_2025(self):
        """
        Excluding conditionally required fields should raise an exception

        NOTE: conditional on `agreement_start_date`>=2025-12-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2025-12-01'
        record['amendment_number'] = 0

        # need `agreement_start_date` for conditionals
        expected_required_fields = ['agreement_value', 'agreement_type',
                                    'recipient_legal_name',
                                    'recipient_country',
                                    'recipient_city', 'description_en',
                                    'description_fr', 'recipient_type',
                                    'prog_name_en', 'prog_name_fr',
                                    'prog_purpose_en', 'prog_purpose_fr',
                                    'agreement_title_en', 'agreement_title_fr',
                                    'agreement_end_date', 'expected_results_en',
                                    'expected_results_fr']

        for field_id in expected_required_fields:
            record[field_id] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_required_fields_2018(self):
        """
        Excluding conditionally required fields should raise an exception

        NOTE: conditional on `agreement_start_date`>=2018-04-01
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2018-04-01'
        record['amendment_number'] = 0

        # need `agreement_start_date` for conditionals
        expected_required_fields = ['agreement_value', 'agreement_type',
                                    'recipient_legal_name',
                                    'recipient_country',
                                    'recipient_city', 'description_en',
                                    'description_fr']

        for field_id in expected_required_fields:
            record[field_id] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception

        NOTE: for some reason there is not parity between pSQL and Excel...
        NOTE: not many fields are required, mainly conditionally required...
        """
        chromo = get_chromo('grants')
        ref_record = chromo['examples']['record'].copy()

        record = {
            'ref_number': ref_record['ref_number'],
            'amendment_number': 0
        }

        expected_required_fields = ['agreement_start_date', 'agreement_value']

        for field_id in expected_required_fields:
            record[field_id] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_excel_required_fields(self):
        """
        Checked expected required fields in Excel.

        NOTE: for some reason there is not parity between pSQL and Excel...
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        record['agreement_start_date'] = '2017-01-01'

        expected_required_fields = ['agreement_type', 'recipient_legal_name',
                                    'recipient_country', 'recipient_city',
                                    'agreement_value', 'agreement_start_date',
                                    'description_en', 'description_fr']

        for field in chromo['fields']:
            if field['datastore_id'] in chromo['datastore_primary_key']:
                continue
            if field.get('excel_required') or field.get('form_required'):
                assert field['datastore_id'] in expected_required_fields
                record[field['datastore_id']] = None

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('grants')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['agreement_type', 'recipient_type',
                                  'recipient_country', 'foreign_currency_type']

        for field in chromo['fields']:
            if field.get('published_resource_computed_field'):
                continue
            if field['datastore_id'] == 'recipient_province':
                # special case for recipient_province, handle below...
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

        record = chromo['examples']['record'].copy()
        record['recipient_country'] = 'CA'
        record['recipient_province'] = 'zzz'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'recipient_province' in err['records'][0]

    def test_filter_script(self):
        """
        Filter out default Registry fields.

        NOTE: csv.DictReader treats every dict value as a string,
              so we need to use Strings here. Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        record = get_chromo('grants')['examples']['record'].copy()

        # filters out record_created, record_modified, user_modified
        record['record_created'] = 'Not Blank'
        record['record_modified'] = 'Not Blank'
        record['user_modified'] = 'Not Blank'

        test_record = filter_generic.test(dict(record))
        assert 'record_created' not in test_record
        assert 'record_modified' not in test_record
        assert 'user_modified' not in test_record


class TestGrantsNil(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestGrantsNil, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='grants', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='grants', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('grants-nil')['examples']['record'].copy()
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
        assert 'fiscal_year, quarter' in err['key'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('grants-nil')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['fiscal_year', 'quarter']

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

    def test_filter_script(self):
        """
        Filter out default Registry fields.

        NOTE: csv.DictReader treats every dict value as a string,
              so we need to use Strings here. Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        record = get_chromo('grants-nil')['examples']['record'].copy()

        # filters out record_created, record_modified, user_modified
        record['record_created'] = 'Not Blank'
        record['record_modified'] = 'Not Blank'
        record['user_modified'] = 'Not Blank'

        test_record = filter_generic.test(dict(record))
        assert 'record_created' not in test_record
        assert 'record_modified' not in test_record
        assert 'user_modified' not in test_record


# (staging fork only): grants monthly
class TestGrantsMonthly(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestGrantsMonthly, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='grantsmonthly', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='grantsmonthly', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('grantsmonthly')['examples']['record']
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
