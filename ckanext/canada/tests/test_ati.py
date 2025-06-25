# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestAti(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestAti, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='ati', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='ati', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        record = get_chromo('ati')['examples']['record']
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
        assert 'request_number' in err['key'][0]

    def test_request_number_comma(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'request_number': 'AA-2020-00,516',
                    'disposition': 'DP',
                    'month':'01',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                    'year': '2020'
                          
                }]
            )
        err = ve.value.error_dict['records'][0]
        print('error', err)
        assert 'request_number' in err

    def test_year_before_2011(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'year': '2010',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'month':'01',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'year' in err

    def test_year_future_date(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'year': '2029',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'month':'01',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'year' in err

    def test_month_negative(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'month':'0',
                    'year': '2029',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'month' in err

    def test_invalid_month(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'month':'13',
                    'year': '2029',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'month' in err

    def test_invalid_month(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'month':'13',
                    'year': '2029',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'pages':'1',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'month' in err

    def test_negative_pages(self):
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'pages':'-1',
                    'month':'13',
                    'year': '2029',
                    'request_number': 'AA-2020-00516',
                    'disposition': 'DP',
                    'summary_en': 'summary',
                    'summary_fr': 'summary french',
                }]
            )
        err = ve.value.error_dict['records'][0]
        assert 'pages' in err


class TestAtiNil(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestAtiNil, self).setup_method(method)

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='ati', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='ati', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        record = get_chromo('ati-nil')['examples']['record']
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
