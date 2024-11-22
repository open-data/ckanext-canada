# -*- coding: UTF-8 -*-
import os
import json
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

COUNTRY_FILE = os.path.dirname(__file__) + '/../tables/choices/country.json'


class TestTravelQ(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestTravelQ, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='travelq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='travelq', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('travelq')['examples']['record']
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
        assert 'ref_number' in err['key'][0]


    def test_destination_format(self):
        record = get_chromo('travelq')['examples']['record']
        partial_err_msg = 'Invalid format for destination'

        with open(COUNTRY_FILE) as f:
            countries = json.load(f)

        # tests correct formats
        for _code, country_names in countries.items():
            _destination = country_names['en'].replace(',', '') + ', ' + country_names['fr'].replace(',', '')
            record['destination_en'] = _destination
            record['destination_fr'] = _destination
            record['destination_2_en'] = _destination
            record['destination_2_fr'] = _destination
            record['destination_other_en'] = _destination
            record['destination_other_fr'] = _destination
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

        # tests some incorrect formats
        incorrect_formats = [
            'St. John, New Brunswick, Canada, Canada',
            'New York',
            'Toronto Canada',
            'Toronto,',
            ',Canada',
            # 'Ottawa, Canada,',  #FIXME: should fail...
        ]
        for incorrect_format in incorrect_formats:
            record['destination_en'] = incorrect_format
            record['destination_fr'] = incorrect_format
            record['destination_2_en'] = incorrect_format
            record['destination_2_fr'] = incorrect_format
            record['destination_other_en'] = incorrect_format
            record['destination_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict['records'][0]
            # NOTE: have to do partial because \uF8FF split formatting does not happen at this level
            expected = {
                'destination_en': [partial_err_msg],
                'destination_fr': [partial_err_msg],
                'destination_2_en': [partial_err_msg],
                'destination_2_fr': [partial_err_msg],
                'destination_other_en': [partial_err_msg],
                'destination_other_fr': [partial_err_msg],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert expected[k][0] in err[k][0]

        # test multi-destination formats
        record['destination_en'] = 'Ottawa, Ontario, Canada'
        record['destination_fr'] = 'Ottawa, Ontario, Canada'
        record['destination_2_en'] = 'Ottawa, Ontario, Canada'
        record['destination_2_fr'] = 'Ottawa, Ontario, Canada'
        record['destination_other_en'] = 'Montreal, Quebec, Canada; Toronto, Ontario, Canada; New York, United States (USA); London, England'
        record['destination_other_fr'] = 'Montreal, Quebec, Canada; Toronto, Ontario, Canada; New York, United States (USA); London, England'
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        # tests some incorrect formats
        incorrect_formats = [
            'St. John, New Brunswick, Canada, Canada; USA, ;',
            'New York; New Hampshire',
            'Toronto Canada; New York (USA)',
            'Toronto,;New York,',
            ',Canada; Halifax, Canada; New Jersey',
            'Ottawa, Canada,; Vancouver; New York',
            'Ottawa, Canada; Mexico City;'
        ]
        for incorrect_format in incorrect_formats:
            record['destination_en'] = 'Ottawa, Canada'
            record['destination_fr'] = 'Ottawa, Canada'
            record['destination_2_en'] = 'Ottawa, Canada'
            record['destination_2_fr'] = 'Ottawa, Canada'
            record['destination_other_en'] = incorrect_format
            record['destination_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict['records'][0]
            #FIXME: expected
            # NOTE: have to do partial because \uF8FF split formatting does not happen at this level
            expected = {
                'destination_other_en': [partial_err_msg],
                'destination_other_fr': [partial_err_msg],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert expected[k][0] in err[k][0]

        # test surrounding white space stripping
        raw_values_expected_values = {
            ' Kingston  , Canada ': 'Kingston, Canada',
            'Ottawa,Canada': 'Ottawa, Canada',
            'Toronto,    Canada   ': 'Toronto, Canada',
            '   Montreal ,  Quebec   ,Canada': 'Montreal, Quebec, Canada',
        }
        for raw_value, excpected_value in raw_values_expected_values.items():
            record['destination_en'] = raw_value
            record['destination_fr'] = raw_value
            record['destination_2_en'] = raw_value
            record['destination_2_fr'] = raw_value
            record['destination_other_en'] = raw_value
            record['destination_other_fr'] = raw_value
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            result = self.lc.action.datastore_search(resource_id=self.resource_id)
            records = result.get('records')
            assert len(records) > 0
            assert records[0]['destination_en'] == excpected_value
            assert records[0]['destination_fr'] == excpected_value
            assert records[0]['destination_2_en'] == excpected_value
            assert records[0]['destination_2_fr'] == excpected_value
            assert records[0]['destination_other_en'] == excpected_value
            assert records[0]['destination_other_fr'] == excpected_value

        # test surrounding white space stripping for multi-destination formats
        raw_values_expected_values = {
            ' Montreal  ,  Quebec  , Canada ;Toronto  ,  Canada;   New York, United States (USA)  ; St. John\'s,Canada': 'Montreal, Quebec, Canada;Toronto, Canada;New York, United States (USA);St. John\'s, Canada',
            'Montreal,Quebec,Canada  ;  Toronto,Canada  ;  New York,United States (USA)  ;  St. John\'s,Canada': 'Montreal, Quebec, Canada;Toronto, Canada;New York, United States (USA);St. John\'s, Canada',
            ' Montreal,Quebec  ,  Canada  ;  Toronto  , Canada  ;  New York ,United States (USA);  St. John\'s,Canada   ': 'Montreal, Quebec, Canada;Toronto, Canada;New York, United States (USA);St. John\'s, Canada',
            'Montreal,  Quebec,Canada ;   Toronto  , Canada;  New York   , United States (USA) ; St. John\'s,Canada  ': 'Montreal, Quebec, Canada;Toronto, Canada;New York, United States (USA);St. John\'s, Canada',
        }
        for raw_value, excpected_value in raw_values_expected_values.items():
            record['destination_en'] = 'Ottawa, Canada'
            record['destination_fr'] = 'Ottawa, Canada'
            record['destination_2_en'] = 'Ottawa, Canada'
            record['destination_2_fr'] = 'Ottawa, Canada'
            record['destination_other_en'] = raw_value
            record['destination_other_fr'] = raw_value
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            result = self.lc.action.datastore_search(resource_id=self.resource_id)
            records = result.get('records')
            assert len(records) > 0
            assert records[0]['destination_other_en'] == excpected_value
            assert records[0]['destination_other_fr'] == excpected_value


class TestTravelQNil(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestTravelQNil, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='travelq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='travelq', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']


    def test_example(self):
        record = get_chromo('travelq-nil')['examples']['record']
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
        assert 'year, month' in err['key'][0]
