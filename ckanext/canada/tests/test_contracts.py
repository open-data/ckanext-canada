# -*- coding: UTF-8 -*-

from io import StringIO

from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization
from ckanext.canada.tests.filters import filter_contracts

from ckanext.recombinant.tables import get_chromo


class TestContracts(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestContracts, self).setup_class()

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

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = dict(
            get_chromo('contracts')['examples']['record'],
            reference_number='this,is,a,failure'
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert err == {'records': [{
            'reference_number': ['Comma is not allowed in Reference Number field'],
        }], 'records_row': 0}

    def test_blank(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'reference_number' in err['key'][0]

    def test_required_fields(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{'reference_number': '42'}])
        err = ve.value.error_dict
        assert err == {
            'records': [{'contract_date': ['This field must not be empty']}],
            'records_row': 0
        }

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'reference_number': '42',
                    'contract_date': '2022-01-01',
                }])
        err = ve.value.error_dict
        assert err == {'records': [{
            'buyer_name': ['This field must not be empty'],
            'commodity_code': ['This field must not be empty'],
            'commodity_type': ['This field must not be empty'],
            'contract_value': ['This field must not be empty'],
            'country_of_vendor': ['This field must not be empty'],
            'delivery_date': ['This field must not be empty'],
            'description_en': ['This field must not be empty'],
            'description_fr': ['This field must not be empty'],
            'economic_object_code': ['This field must not be empty'],
            'former_public_servant': ['This field must not be empty'],
            'indigenous_business': ['This field must not be empty'],
            'indigenous_business_excluding_psib': ['This field must not be empty'],
            'instrument_type': ['This field must not be empty'],
            'intellectual_property': ['This field must not be empty'],
            'land_claims': ['This field must not be empty'],
            'limited_tendering_reason': ['This field must not be empty'],
            'ministers_office': ['This field must not be empty'],
            'original_value': ['This field must not be empty'],
            'procurement_id': ['This field must not be empty'],
            'reporting_period': ['This field must not be empty'],
            'solicitation_procedure': ['This field must not be empty'],
            'trade_agreement': ['This field must not be empty'],
            'trade_agreement_exceptions': ['This field must not be empty'],
            'vendor_name': ['This field must not be empty'],
            'vendor_postal_code': ['This field must not be empty'],
        }], 'records_row': 0}

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'reference_number': '42',
                    'contract_date': '2019-01-01',
                }])
        err = ve.value.error_dict
        assert err == {'records': [{
            'agreement_type_code': ['This field must not be empty'],
            'commodity_code': ['This field must not be empty'],
            'commodity_type': ['This field must not be empty'],
            'contract_value': ['This field must not be empty'],
            'country_of_vendor': ['This field must not be empty'],
            'delivery_date': ['This field must not be empty'],
            'description_en': ['This field must not be empty'],
            'description_fr': ['This field must not be empty'],
            'economic_object_code': ['This field must not be empty'],
            'former_public_servant': ['This field must not be empty'],
            'indigenous_business_excluding_psib': ['This field must not be empty'],
            'instrument_type': ['This field must not be empty'],
            'intellectual_property': ['This field must not be empty'],
            'original_value': ['This field must not be empty'],
            'procurement_id': ['This field must not be empty'],
            'reporting_period': ['This field must not be empty'],
            'trade_agreement_exceptions': ['This field must not be empty'],
            'vendor_name': ['This field must not be empty'],
        }], 'records_row': 0}

        # Nothing(!) required for contracts < 2019-01-01
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[{
                'reference_number': '42',
                'contract_date': '2018-12-31',
            }])

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
        err = ve.value.error_dict
        assert err == {'records': [{
            'vendor_postal_code': ['This field must not be empty'],
            'buyer_name': ['This field must not be empty'],
            'trade_agreement': ['This field must not be empty'],
            'agreement_type_code': ['Discontinued as of 2022-01-01'],
            'land_claims': ['This field must not be empty'],
            'indigenous_business': ['This field must not be empty'],
        }], 'records_row': 0}

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
        assert err == {'records': [{
            'trade_agreement': ['If the value XX (none) is entered, then no other value can be entered in this field.'],
            'land_claims': ['If the value NA (not applicable) is entered, then no other value can be entered in this field.'],
            'limited_tendering_reason': ['If the value 00 (none) is entered, then no other value can be entered in this field.'],
            'trade_agreement_exceptions': ['If the value 00 (none) is entered, then no other value can be entered in this field.'],
        }], 'records_row': 0}

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
        assert err == {'records': [{
            'buyer_name': ['This field must be populated with an NA if an amendment is disclosed under Instrument Type'],
            'economic_object_code': ['If N/A, then Instrument Type must be identified as a standing offer/supply arrangement (SOSA)'],
            'number_of_bids': ['This field must be populated with a 1 if the solicitation procedure is identified as non-competitive (TN) or Advance Contract Award Notice (AC).'],
        }], 'records_row': 0}

        record = dict(
            get_chromo('contracts')['examples']['record'],
            trade_agreement=['CA'],
            agreement_type_code='0',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert err == {'records': [{
            'agreement_type_code': ['Must be left blank when trade agreements specified'],
        }], 'records_row': 0}

        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            solicitation_procedure='TC',
            trade_agreement=['CA'],
            limited_tendering_reason=['00'],
            indigenous_business_excluding_psib='Y',
            indigenous_business='MS',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert err == {'records': [{
            'limited_tendering_reason': ['If TC, TN or AC is selected in the Solicitation Procedure data field with a value other than XX (None) selected in the Trade Agreement data field, then a Limited Tendering value other than 00 (none) must be entered.'],
            'solicitation_procedure': ['If “TC” (Competitive - Traditional), “TN” (Non-Competitive) or “AC” (Advanced Contract Award Notice) is selected and trade agreement with a value other than “XX” (None) is selected, limited tendering cannot have a value of “0” or “00” (None).'],
            'indigenous_business_excluding_psib': ['This field must be N, No or Non, if the Procurement Strategy for Aboriginal Business field is MS or VS.'],
        }], 'records_row': 0}

        record = dict(
            get_chromo('contracts')['examples']['record'],
            contract_date='2022-01-01',
            instrument_type='A',
            award_criteria='1',
            article_6_exceptions='1',
            solicitation_procedure='OB',
            buyer_name='NA',
        )
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert err == {'records': [{
            'award_criteria': ['If this field is populated, it must be with a “0” if the procurement was identified as non-competitive (TN) or advance contract award notice (AC) or was identified as an Amendment (A) in the Instrument type data field.'],
            'article_6_exceptions': ['This field may only be populated with “0” if the procurement was identified as competitive (open bidding (OB), traditional competitive (TC) or selective tendering (ST)).'],
        }], 'records_row': 0}

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
        assert err == {'records': [{
            'economic_object_code': ['This field is limited to only 3 or 4 digits.'],
            'commodity_code': ['The field is limited to eight alpha-numeric digits or less.'],
        }], 'records_row': 0}

    def test_postal_code(self):
        record = dict(
            get_chromo('contracts')['examples']['record'],
            vendor_postal_code='1A1')
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        err = ve.value.error_dict
        assert err == {'records': [{
            'vendor_postal_code': [
                'This field must contain the first three digits of a postal code '
                'in A1A format or the value "NA"'
            ],
        }], 'records_row': 0}


def test_contracts_filter():
    inf = StringIO(
        'a,b,record_created,record_modified,user_modified\n'
        '1,2,3,4,5\n'
    )
    outf = StringIO()
    filter_contracts.main(inf, outf)
    assert outf.getvalue() == 'a,b\r\n1,2\r\n'
