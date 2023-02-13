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
        expected = 'reference_number'
        assert 'key' in err
        assert expected in err['key'][0]


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
        expected = 'ministers_office'
        assert 'records' in err
        assert expected in err['records'][0]


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
        err = ve.value.error_dict
        expected = ['vendor_postal_code',
                    'buyer_name',
                    'trade_agreement',
                    'agreement_type_code',
                    'land_claims',
                    'indigenous_business']
        assert 'records' in err
        for k in set(err['records'][0]):
            assert k in expected


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
        err = ve.value.error_dict
        expected = ['trade_agreement',
                    'land_claims',
                    'limited_tendering_reason',
                    'trade_agreement_exceptions']
        assert 'records' in err
        for k in set(err['records'][0]):
            assert k in expected


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
        err = ve.value.error_dict
        expected = ['buyer_name',
                    'economic_object_code',
                    'number_of_bids']
        assert 'records' in err
        for k in set(err['records'][0]):
            assert k in expected


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
        err = ve.value.error_dict
        expected = ['economic_object_code',
                    'commodity_code']
        assert 'records' in err
        for k in set(err['records'][0]):
            assert k in expected


    def test_postal_code(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            vendor_postal_code='1A1')
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        expected = 'vendor_postal_code'
        assert 'records' in err
        assert expected in err['records'][0]
