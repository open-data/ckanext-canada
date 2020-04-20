# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import Organization

from ckanext.recombinant.tables import get_chromo

class TestContracts(FunctionalTestBase):
    def setup(self):
        super(TestContracts, self).setup()
        org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='contracts', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='contracts', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('contracts')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        lc = LocalCKAN()
        assert_raises(ValidationError,
            lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])

    def test_ministers_office_missing(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2019-06-21',
            ministers_office=None)
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'ministers_office': ['This field must not be empty'],
        }
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))

    def test_ministers_office(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2019-06-21',
            ministers_office='N')
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_2022_fields(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            vendor_postal_code=None,
            buyer_name='',
            trade_agreement='',
            agreement_type_code='Z',
            land_claims=None,
            aboriginal_business='',
        )
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'vendor_postal_code': ['This field must not be empty'],
            'buyer_name': ['This field must not be empty'],
            'trade_agreement': ['This field must not be empty'],
            'agreement_type_code': ['Discontinued as of 2022-01-01'],
            'land_claims': ['This field must not be empty'],
            'aboriginal_business': ['This field must not be empty'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))

    def test_multi_field_errors(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            trade_agreement=['XX', 'NA'],
            land_claims=['JN', 'NA'],
            limited_tendering_reason=['00', '05'],
            trade_agreement_exceptions=['00', '01'],
            socioeconomic_indicator=['FP', 'NA'],
        )
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'trade_agreement': [
                'If the value XX (none) is entered, then no other value '
                'can be entered in this field.'],
            'land_claims': [
                'If the value NA (not applicable) is entered, then no other '
                'value can be entered in this field.'],
            'limited_tendering_reason': [
                'If the value 00 (none) is entered, then no other value can '
                'be entered in this field.'],
            'trade_agreement_exceptions': [
                'If the value 00 (none) is entered, then no other value can '
                'be entered in this field.'],
            'socioeconomic_indicator': [
                'If the value NA (None) is entered, then no other value can '
                'be entered in this field'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))

    def test_inter_field_errors(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            instrument_type='A',
            buyer_name='Smith',
            economic_object_code='NA',
            trade_agreement=['CA'],
            land_claims=['JN'],
            award_criteria='0',
        )
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'buyer_name': [
                'This field must be populated with an NA '
                'if an amendment is disclosed under Instrument Type'],
            'economic_object_code': [
                'If N/A, then Instrument Type must be identified '
                'as a standing offer/supply arrangement (SOSA)'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))

    def test_postal_code(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            vendor_postal_code='1A1')
        with assert_raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'vendor_postal_code': [
                'This field must contain the first three digits of a postal code '
                'in A1A format or the value "NA"'],
        }
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))
