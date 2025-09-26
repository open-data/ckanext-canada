# -*- coding: UTF-8 -*-
import os
import json
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

COUNTRY_FILE = os.path.dirname(__file__) + '/../tables/choices/country.json'


class TestTravelQ(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestTravelQ, self).setup_class()

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
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'ref_number' in err['key'][0]

    def test_dates(self):
        """
        Start Date cannot be in the future, and dates must be chronological
        """
        record = get_chromo('travelq')['examples']['record']

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

    def test_disclosure_group(self):
        """
        Disclosure Group is required if on or after April 1st 2025
        """
        record = get_chromo('travelq')['examples']['record']

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

    def test_destination_format(self):
        """
        Destination format is validated on or after April 1st 2025
        """
        record = get_chromo('travelq')['examples']['record']
        partial_err_msg = 'Invalid format for destination'

        record['start_date'] = '2025-04-21'
        record['end_date'] = '2025-04-24'
        record['destination_en'] = 'England'
        record['destination_fr'] = 'England'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]
            # NOTE: have to do partial because \uF8FF split formatting does not happen at this level
            expected = {
                'destination_en': [partial_err_msg],
                'destination_fr': [partial_err_msg],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert k in expected
                assert expected[k][0] in err[k][0]
        model.Session.rollback()
        record['start_date'] = '2024-04-21'
        record['end_date'] = '2024-04-24'
        record['destination_en'] = 'England'
        record['destination_fr'] = 'England'

        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        record['start_date'] = '2025-04-21'
        record['end_date'] = '2025-04-24'

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
            'Ottawa, Canada,',
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
            model.Session.rollback()
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
                assert k in expected
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
        incorrect_formats_error_count = {
            'St. John, New Brunswick, Canada, Canada; USA, ;': 3,
            'New York; New Hampshire': 2,
            'Toronto Canada; New York (USA)': 2,
            'Toronto,;New York,': 2,
            ',Canada; Halifax, Canada; New Jersey': 2,
            'Ottawa, Canada,; Vancouver; New York': 3,
            'Ottawa, Canada; Mexico City;': 2,
            'Ottawa': 1,
            'Ottawa,': 1,
        }
        for incorrect_format, error_count in incorrect_formats_error_count.items():
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
            model.Session.rollback()
            err = ve.value.error_dict['records'][0]
            # NOTE: have to do partial because \uF8FF split formatting does not happen at this level
            expected = {
                'destination_other_en': [partial_err_msg],
                'destination_other_fr': [partial_err_msg],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert k in expected
                assert len(err[k]) == error_count
                for _i in range(0, error_count):
                    assert expected[k][0] in err[k][_i]

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
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestTravelQNil, self).setup_class()

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
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'year, month' in err['key'][0]
