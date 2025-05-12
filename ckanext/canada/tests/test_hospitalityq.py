# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestHospitalityQ(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestHospitalityQ, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('hospitalityq')['examples']['record']
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

    def test_dates(self):
        """
        Start Date cannot be in the future, and dates must be chronological
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2999999-01-29'
        record['end_date'] = '2999999-01-30'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'start_date' in err
            assert 'end_date' in err

        record['start_date'] = '2024-01-29'
        record['end_date'] = '2024-01-15'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'start_date' in err

    def test_attendees(self):
        """
        Attendee fields cannot be zero or below if on or after April 1st 2025
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2025-04-29'
        record['end_date'] = '2025-04-30'
        record['employee_attendees'] = -2
        record['guest_attendees'] = -5
        record['employee_attendees'] = 0

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'employee_attendees' in err
            assert 'guest_attendees' in err
            assert 'employee_attendees' in err

        record['start_date'] = '2024-04-29'
        record['end_date'] = '2024-04-30'

        self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])

    def test_disclosure_group(self):
        """
        Disclosure Group is required if on or after April 1st 2025
        """
        record = get_chromo('hospitalityq')['examples']['record']

        record['start_date'] = '2025-04-21'
        record['end_date'] = '2025-04-24'
        record['disclosure_group'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            err = ve.value.error_dict['records'][0]

            assert 'disclosure_group' in err

        record['start_date'] = '2024-04-21'
        record['end_date'] = '2024-04-24'
        record['disclosure_group'] = 'SLE'

        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_vendor_format(self):
        record = get_chromo('hospitalityq')['examples']['record']
        record['start_date'] = '2024-04-21'
        record['end_date'] = '2024-04-24'

        # tests some incorrect formats
        incorrect_formats = [
            'Starbucks ;',
            'Tim Hortons & Starbucks ;   ',
            'Les Impertinentes ; ; Les Street Monkeys',
            'Starbucks, Montanas ; ',
        ]
        for incorrect_format in incorrect_formats:
            record['vendor_other_en'] = incorrect_format
            record['vendor_other_fr'] = incorrect_format
            with pytest.raises(ValidationError) as ve:
                self.lc.action.datastore_upsert(
                    resource_id=self.resource_id,
                    records=[record])
            err = ve.value.error_dict['records'][0]
            expected = {
                'vendor_other_en': ["Invalid format for multiple commercial establishments or vendors. Use <Vendor Name>;<Vendor 2 Name> (e.g. Les Impertinentes;Les Street Monkeys)"],
                'vendor_other_fr': ["Invalid format for multiple commercial establishments or vendors. Use <Vendor Name>;<Vendor 2 Name> (e.g. Les Impertinentes;Les Street Monkeys)"],
            }
            for k in set(err) | set(expected):
                assert k in err
                assert k in expected
                assert err[k] == expected[k]

        # test surrounding white space stripping
        raw_values_expected_values = {
            ' Les Impertinentes ; Les Street Monkeys ': 'Les Impertinentes;Les Street Monkeys',
            'Les Impertinentes ; Les Street Monkeys ;  Starbucks ': 'Les Impertinentes;Les Street Monkeys;Starbucks',
            '  Les Impertinentes  ;  Les Street Monkeys  ;  Tim Hortons  ': 'Les Impertinentes;Les Street Monkeys;Tim Hortons',
            '  Les Impertinentes  ': 'Les Impertinentes',
        }
        for raw_value, excpected_value in raw_values_expected_values.items():
            record['vendor_other_en'] = raw_value
            record['vendor_other_fr'] = raw_value
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
            result = self.lc.action.datastore_search(resource_id=self.resource_id)
            records = result.get('records')
            assert len(records) > 0
            assert records[0]['vendor_other_en'] == excpected_value
            assert records[0]['vendor_other_fr'] == excpected_value


class TestHospitalityQNil(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestHospitalityQNil, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='hospitalityq', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='hospitalityq', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        record = get_chromo('hospitalityq-nil')['examples']['record']
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
