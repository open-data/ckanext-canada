# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestContracts(object):
    @classmethod
    def setup_class(self):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

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
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
            records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None


    def test_ministers_office_missing(self):
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2019-06-21',
            ministers_office=None)
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'ministers_office': ['This field must not be empty'],
        }
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]


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
            indigenous_business='',
        )
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
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
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            trade_agreement=['XX', 'NA'],
            land_claims=['JN', 'NA'],
            limited_tendering_reason=['00', '05'],
            trade_agreement_exceptions=['00', '01'],
        )
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
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
            solicitation_procedure='TN',
        )
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
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
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            economic_object_code='467782',
            commodity_code='K23HG367BU',
        )
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
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
        lc = LocalCKAN()
        record = dict(
            get_chromo('contracts')['examples']['record'],
            vendor_postal_code='1A1')
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict['records'][0]
        expected = {
            'vendor_postal_code': [
                'This field must contain the first three digits of a postal code '
                'in A1A format or the value "NA"'],
        }
        for k in set(err) | set(expected):
            assert k in err
            assert err[k] == expected[k]
