# -*- coding: UTF-8 -*-
import sys
import os
from importlib import util

from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

filter_service_std_path = os.path.join(os.path.dirname(str(__file__)), '../../../bin/filter/filter_service_std.py')
spec = util.spec_from_file_location("canada.bin.filters.service_std", filter_service_std_path)
filter_service_std = util.module_from_spec(spec)
sys.modules["canada.bin.filters.service_std"] = filter_service_std
spec.loader.exec_module(filter_service_std)


class TestService(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestService, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']
        self.resource_cid = rval['resources'][1]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('service')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('service')['examples']['record'].copy()
        record['service_id'] = 'this,is,a,failure'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'service_id' in err['records'][0]
        assert err['records'][0]['service_id'] == ['Comma is not allowed in Service ID Number field']

    def test_foreign_constraint(self):
        """
        Trying to delete a Service record when there are Standard records referencing it should raise an exception
        """
        record = get_chromo('service')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])
        record = get_chromo('service-std')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_cid,
            records=[record])
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_records_delete(
                resource_id=self.resource_id,
                filters={})
        err = ve.value.error_dict
        assert 'constraint_info' in err
        assert err['constraint_info']['ref_keys'] == 'fiscal_yr, service_id'

    def test_blank(self):
        """
        Should raise a Database key error
        """
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'fiscal_yr, service_id' in err['key'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception
        """
        chromo = get_chromo('service')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['service_name_en', 'service_name_fr',
                                    'service_description_en', 'service_description_fr',
                                    'service_type', 'service_recipient_type',
                                    'service_scope', 'client_target_groups',
                                    'program_id', 'client_feedback_channel',
                                    'automated_decision_system', 'service_fee',
                                    'os_account_registration', 'os_authentication',
                                    'os_application', 'os_decision', 'os_issuance',
                                    'os_issue_resolution_feedback', 'sin_usage',
                                    'cra_bn_identifier_usage', 'num_phone_enquiries',
                                    'num_applications_by_phone', 'num_website_visits',
                                    'num_applications_online', 'num_applications_in_person',
                                    'num_applications_by_mail', 'num_applications_by_email',
                                    'num_applications_by_fax', 'num_applications_by_other']

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
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_conditional_fields(self):
        """
        Test conditionally required fields
        """
        chromo = get_chromo('service')
        record = chromo['examples']['record'].copy()

        # automated_decision_system_description_en and automated_decision_system_description_fr
        # should be required if automated_decision_system is Y.
        record['automated_decision_system'] = 'Y'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'automated_decision_system_description_en' in err['records'][0]
        assert 'automated_decision_system_description_fr' in err['records'][0]

        record = chromo['examples']['record'].copy()

        # os_comments_client_interaction_en and os_comments_client_interaction_fr
        # should be required if any of the online service fields are NA.
        online_service_fields = ['os_account_registration', 'os_authentication',
                                 'os_application', 'os_decision', 'os_issuance',
                                 'os_issue_resolution_feedback']

        for online_service_field in online_service_fields:
            record[online_service_field] = 'NA'
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict
            assert 'records' in err
            assert 'os_comments_client_interaction_en' in err['records'][0]
            assert 'os_comments_client_interaction_fr' in err['records'][0]
            record[online_service_field] = 'Y'

        record = chromo['examples']['record'].copy()

        # special_remarks_en and special_remarks_fr should be
        # required if num_applications_by_other is greater than zero.
        record['num_applications_by_other'] = 12
        record['special_remarks_en'] = None
        record['special_remarks_fr'] = None
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'special_remarks_en' in err['records'][0]
        assert 'special_remarks_fr' in err['records'][0]

    def test_duolang_fields(self):
        """
        Fields with both _en and _fr should require eachother
        """
        chromo = get_chromo('service')
        record = chromo['examples']['record'].copy()

        record['num_applications_by_other'] = 0

        record['automated_decision_system_description_en'] = 'Not Blank'
        record['automated_decision_system_description_fr'] = None

        record['os_comments_client_interaction_en'] = 'Not Blank'
        record['os_comments_client_interaction_fr'] = None

        record['special_remarks_en'] = 'Not Blank'
        record['special_remarks_fr'] = None

        record['service_uri_en'] = 'Not Blank'
        record['service_uri_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'automated_decision_system_description_fr' in err['records'][0]
        assert 'os_comments_client_interaction_fr' in err['records'][0]
        assert 'special_remarks_fr' in err['records'][0]
        assert 'service_uri_fr' in err['records'][0]

        record['automated_decision_system_description_fr'] = 'Not Blank'
        record['automated_decision_system_description_en'] = None

        record['os_comments_client_interaction_fr'] = 'Not Blank'
        record['os_comments_client_interaction_en'] = None

        record['special_remarks_fr'] = 'Not Blank'
        record['special_remarks_en'] = None

        record['service_uri_fr'] = 'Not Blank'
        record['service_uri_en'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'automated_decision_system_description_en' in err['records'][0]
        assert 'os_comments_client_interaction_en' in err['records'][0]
        assert 'special_remarks_en' in err['records'][0]
        assert 'service_uri_en' in err['records'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('service')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['fiscal_yr', 'service_type', 'service_recipient_type',
                                  'service_scope', 'client_target_groups', 'program_id',
                                  'client_feedback_channel', 'automated_decision_system',
                                  'service_fee', 'os_account_registration',
                                  'os_authentication', 'os_application', 'os_decision',
                                  'os_issuance', 'os_issue_resolution_feedback',
                                  'last_service_review', 'last_service_improvement',
                                  'sin_usage', 'cra_bn_identifier_usage']

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
        err = ve.value.error_dict
        assert 'records' in err
        for expected_choice_field in expected_choice_fields:
            assert expected_choice_field in err['records'][0]

    def test_max_chars(self):
        """
        Over max character field values should raise an exception
        """
        chromo = get_chromo('service')
        record = chromo['examples']['record'].copy()

        expect_maxchar_fields = ['service_name_en', 'service_name_fr',
                                 'service_description_en', 'service_description_fr',
                                 'automated_decision_system_description_en',
                                 'automated_decision_system_description_fr',
                                 'os_comments_client_interaction_en',
                                 'os_comments_client_interaction_fr',
                                 'special_remarks_en', 'special_remarks_fr',
                                 'service_uri_en', 'service_uri_fr']

        for field in chromo['fields']:
            if field.get('max_chars'):
                assert field['datastore_id'] in expect_maxchar_fields
                record[field['datastore_id']] = 'xx' * field.get('max_chars')

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        for maxchar_field in expect_maxchar_fields:
            assert maxchar_field in err['records'][0]

    def test_int_na_nd(self):
        """
        Special ND, NA, or positive integer fields
        """
        record = get_chromo('service')['examples']['record'].copy()

        expected_int_na_nd_fields = ['num_phone_enquiries', 'num_applications_by_phone',
                                     'num_website_visits', 'num_applications_online',
                                     'num_applications_in_person',
                                     'num_applications_by_mail',
                                     'num_applications_by_email',
                                     'num_applications_by_fax',
                                     'num_applications_by_other']

        for int_na_nd_field in expected_int_na_nd_fields:
            record[int_na_nd_field] = 'BLOOP'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        for int_na_nd_field in expected_int_na_nd_fields:
            assert int_na_nd_field in err['records'][0]

        for int_na_nd_field in expected_int_na_nd_fields:
            record[int_na_nd_field] = -66

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        for int_na_nd_field in expected_int_na_nd_fields:
            assert int_na_nd_field in err['records'][0]


class TestStdService(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestStdService, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='service', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='service', owner_org=org['name'])

        self.resource_pid = rval['resources'][0]['id']
        self.resource_id = rval['resources'][1]['id']

    def _make_parent_record(self):
        record = get_chromo('service')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_pid,
            records=[record])

    def test_example(self):
        """
        Example data should load
        """
        self._make_parent_record()
        record = get_chromo('service-std')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('service-std')['examples']['record'].copy().copy()
        record['service_id'] = 'this,is,a,failure'
        record['service_standard_id'] = 'this,is,a,failure'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'service_id' in err['records'][0]
        assert 'service_standard_id' in err['records'][0]
        assert err['records'][0]['service_id'] == ['Comma is not allowed in Service ID Number field']
        assert err['records'][0]['service_standard_id'] == ['Comma is not allowed in Service Standard ID field']

    def test_foreign_constraint(self):
        """
        Trying to create a Standard record referencing a nonexistent Service record should raise an exception
        """
        record = get_chromo('service-std')['examples']['record'].copy()
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'constraint_info' in err
        assert err['constraint_info']['ref_keys'] == 'fiscal_yr, service_id'

    def test_blank(self):
        """
        Should raise a Database key error
        """
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'fiscal_yr, service_id, service_standard_id' in err['key'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception
        """
        self._make_parent_record()
        chromo = get_chromo('service-std')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['service_name_en', 'service_name_fr',
                                    'service_standard_en', 'service_standard_fr',
                                    'type', 'channel', 'standards_targets_uri_en',
                                    'standards_targets_uri_fr']

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
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_duolang_fields(self):
        """
        Fields with both _en and _fr should require eachother
        """
        self._make_parent_record()
        record = get_chromo('service-std')['examples']['record'].copy().copy()

        record['channel_comments_en'] = 'Not Blank'
        record['channel_comments_fr'] = None

        record['comments_en'] = 'Not Blank'
        record['comments_fr'] = None

        record['performance_results_uri_en'] = 'Not Blank'
        record['performance_results_uri_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'channel_comments_fr' in err['records'][0]
        assert 'comments_fr' in err['records'][0]
        assert 'performance_results_uri_fr' in err['records'][0]

        record['channel_comments_fr'] = 'Not Blank'
        record['channel_comments_en'] = None

        record['comments_fr'] = 'Not Blank'
        record['comments_en'] = None

        record['performance_results_uri_fr'] = 'Not Blank'
        record['performance_results_uri_en'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'channel_comments_en' in err['records'][0]
        assert 'comments_en' in err['records'][0]
        assert 'performance_results_uri_en' in err['records'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('service-std')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['fiscal_yr', 'type', 'channel']

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
        err = ve.value.error_dict
        assert 'records' in err
        for expected_choice_field in expected_choice_fields:
            assert expected_choice_field in err['records'][0]

    def test_max_chars(self):
        """
        Over max character field values should raise an exception
        """
        self._make_parent_record()
        chromo = get_chromo('service-std')
        record = chromo['examples']['record'].copy()

        expect_maxchar_fields = ['service_name_en', 'service_name_fr',
                                 'service_standard_en', 'service_standard_fr',
                                 'channel_comments_en', 'channel_comments_fr',
                                 'comments_en', 'comments_fr',
                                 'standards_targets_uri_en',
                                 'standards_targets_uri_fr',
                                 'performance_results_uri_en',
                                 'performance_results_uri_fr']

        for field in chromo['fields']:
            if field.get('max_chars'):
                assert field['datastore_id'] in expect_maxchar_fields
                record[field['datastore_id']] = 'xx' * field.get('max_chars')

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        for maxchar_field in expect_maxchar_fields:
            assert maxchar_field in err['records'][0]

    def test_integers(self):
        """
        Range and positive integer validation
        """
        self._make_parent_record()
        chromo = get_chromo('service-std')
        record = chromo['examples']['record'].copy()

        # target should be inbetween 0 and 1 inclusively.
        record['target'] = -66

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'target' in err['records'][0]

        record['target'] = 66

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'target' in err['records'][0]

        # volume_meeting_target and total_volume should be positive

        record = chromo['examples']['record'].copy()

        record['volume_meeting_target'] = -66
        record['total_volume'] = -66

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'volume_meeting_target' in err['records'][0]
        assert 'total_volume' in err['records'][0]

    def test_filter_script(self):
        """
        The calculations for performance and target_met
        should be correct for the required Business Logic
        """
        self._make_parent_record()
        chromo = get_chromo('service-std')
        record = chromo['examples']['record'].copy()

        record['target'] = '0.2'
        record['volume_meeting_target'] = '0'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.0
        assert test_record['target_met'] == 'N'


        record['target'] = '0.2'
        record['volume_meeting_target'] = '5'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.1
        assert test_record['target_met'] == 'N'

        record['target'] = '0.2'
        record['volume_meeting_target'] = '10'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.2
        assert test_record['target_met'] == 'Y'

        record['target'] = '0.2'
        record['volume_meeting_target'] = '30'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.6
        assert test_record['target_met'] == 'Y'

        record['target'] = '0'
        record['volume_meeting_target'] = '10'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.2
        assert test_record['target_met'] == 'NA'

        record['target'] = '0.0'
        record['volume_meeting_target'] = '10'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.2
        assert test_record['target_met'] == 'NA'

        record['target'] = None
        record['volume_meeting_target'] = '10'
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] == 0.2
        assert test_record['target_met'] == 'NA'

        record['target'] = 0.2
        record['volume_meeting_target'] = None
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = None
        record['volume_meeting_target'] = None
        record['total_volume'] = '50'
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = None
        record['volume_meeting_target'] = None
        record['total_volume'] = None
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = 0.2
        record['volume_meeting_target'] = 10
        record['total_volume'] = None
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = 0.2
        record['volume_meeting_target'] = None
        record['total_volume'] = None
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = 0.2
        record['volume_meeting_target'] = 10
        record['total_volume'] = 0
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'

        record['target'] = 0.2
        record['volume_meeting_target'] = 0
        record['total_volume'] = 0
        test_record = filter_service_std.test(dict(record))
        assert test_record['performance'] is None
        assert test_record['target_met'] == 'NA'
