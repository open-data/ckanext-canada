# -*- coding: UTF-8 -*-
import requests
import json
import random
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

DESTINATION_ENDPOINT = 'https://restcountries.com/v3.1/all?fields=name,capital'


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

        # tests correct formats
        destinations = requests.get(DESTINATION_ENDPOINT, stream=True)
        destinations = json.loads(destinations.content)
        for destination in destinations:
            _destination = self._insert_random_spaces((destination.get('capital', ['NaNd'])[0] if destination.get('capital') else 'NaNd').replace(',', '') + ', ' + destination.get('name', {}).get('common', 'NaNd').replace(',', ''))
            record['destination_en'] = _destination
            record['destination_fr'] = _destination
            record['destination_2_en'] = _destination
            record['destination_2_fr'] = _destination
            record['destination_3_en'] = _destination
            record['destination_3_fr'] = _destination
            record['destination_other_en'] = _destination
            record['destination_other_fr'] = _destination
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

        # tests some incorrect formats
        incorrect_formats = [
            'St. John, New Brunswick, Canada',
            'New York',
            'Toronto Canada',
            'Toronto,',
            ',Canada',
            'Ottawa, Canada,',
            'Ottawa, Canada;'
        ]
        for incorrect_format in incorrect_formats:
            record['destination_en'] = incorrect_format
            record['destination_fr'] = incorrect_format
            record['destination_2_en'] = incorrect_format
            record['destination_2_fr'] = incorrect_format
            record['destination_3_en'] = incorrect_format
            record['destination_3_fr'] = incorrect_format
            record['destination_other_en'] = incorrect_format
            record['destination_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict['records'][0]
            expected = {
                'destination_en': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_fr': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_2_en': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_2_fr': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_3_en': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_3_fr': ["Invalid format for destination. Use {City Name}, {Country Name} (e.g. Ottawa, Canada or New York City, United States of America)"],
                'destination_other_en': ["Invalid format for multiple destinations. Use {City Name}, {Country Name};{City 2 Name}, {Country 2 Name} (e.g. Ottawa, Canada;New York City, United States of America)"],
                'destination_other_fr': ["Invalid format for multiple destinations. Use {City Name}, {Country Name};{City 2 Name}, {Country 2 Name} (e.g. Ottawa, Canada;New York City, United States of America)"],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert err[k] == expected[k]

        # test multi-destination formats
        record['destination_en'] = 'Ottawa, Canada'
        record['destination_fr'] = 'Ottawa, Canada'
        record['destination_2_en'] = 'Ottawa, Canada'
        record['destination_2_fr'] = 'Ottawa, Canada'
        record['destination_3_en'] = 'Ottawa, Canada'
        record['destination_3_fr'] = 'Ottawa, Canada'
        record['destination_other_en'] = 'Montreal, Canada; Toronto, Canada; New York, United States (USA); St. John\'s, Canada'
        record['destination_other_fr'] = 'Montreal, Canada; Toronto, Canada; New York, United States (USA); St. John\'s, Canada'
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

        # tests some incorrect formats
        incorrect_formats = [
            'St. John, New Brunswick, Canada; USA, ;',
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
            record['destination_3_en'] = 'Ottawa, Canada'
            record['destination_3_fr'] = 'Ottawa, Canada'
            record['destination_other_en'] = incorrect_format
            record['destination_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict['records'][0]
            expected = {
                'destination_other_en': ["Invalid format for multiple destinations. Use {City Name}, {Country Name};{City 2 Name}, {Country 2 Name} (e.g. Ottawa, Canada;New York City, United States of America)"],
                'destination_other_fr': ["Invalid format for multiple destinations. Use {City Name}, {Country Name};{City 2 Name}, {Country 2 Name} (e.g. Ottawa, Canada;New York City, United States of America)"],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert err[k] == expected[k]


    def _insert_random_spaces(self, s):
        s = list(s)
        for i in range(len(s)-1):
            while random.randrange(2):
                s[i] = s[i] + ' '
        return ''.join(s)


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
