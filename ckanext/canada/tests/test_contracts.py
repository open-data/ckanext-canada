# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestContracts(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='contracts', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='contracts', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('contracts')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
            records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'reference_number' in err['key'][0]


    def test_ministers_office_missing(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2019-06-21',
            ministers_office=None)
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'ministers_office' in err['records'][0]


    def test_ministers_office(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2019-06-21',
            ministers_office='N')
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_2022_fields(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            vendor_postal_code=None,
            buyer_name='',
            trade_agreement='',
            agreement_type_code='Z',
            land_claims=None,
            indigenous_business='',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'vendor_postal_code': ['This field must not be empty'],
            'buyer_name': ['This field must not be empty'],
            'trade_agreement': ['This field must not be empty'],
            'agreement_type_code': ['Discontinued as of 2022-01-01'],
            'land_claims': ['This field must not be empty'],
            'indigenous_business': ['This field must not be empty'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]


    def test_multi_field_errors(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            trade_agreement=['XX', 'NA'],
            land_claims=['JN', 'NA'],
            limited_tendering_reason=['00', '05'],
            trade_agreement_exceptions=['00', '01'],
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
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
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]


    def test_inter_field_errors(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            instrument_type='A',
            buyer_name='Smith',
            economic_object_code='NA',
            trade_agreement=['CA'],
            land_claims=['JN'],
            award_criteria='0',
            solicitation_procedure='TN',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'buyer_name': [
                'This field must be populated with an NA '
                'if an amendment is disclosed under Instrument Type'],
            'economic_object_code': [
                'If N/A, then Instrument Type must be identified '
                'as a standing offer/supply arrangement (SOSA)'],
            'number_of_bids':[
                'This field must be populated with a 1 if the solicitation procedure is '
                'identified as non-competitive (TN) or Advance Contract Award Notice (AC).'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]


    def test_field_length_errors(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            economic_object_code='467782',
            commodity_code='K23HG367BU',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'economic_object_code': ['This field is limited to only 3 or 4 digits.'],
            'commodity_code': ['The field is limited to eight alpha-numeric digits or less.'],
        }
        assert isinstance(err, dict), err
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]


    def test_postal_code(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            vendor_postal_code='1A1')
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'vendor_postal_code' in err['records'][0]
