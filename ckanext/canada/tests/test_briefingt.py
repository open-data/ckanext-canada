# -*- coding: UTF-8 -*-
import sys
import os
from importlib import util

from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan import model
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


filter_generic_path = os.path.join(os.path.dirname(str(__file__)), '../../../bin/filter/filter_modified_created.py')
spec = util.spec_from_file_location("canada.bin.filters.generic", filter_generic_path)
filter_generic = util.module_from_spec(spec)
sys.modules["canada.bin.filters.generic"] = filter_generic
spec.loader.exec_module(filter_generic)


class TestBriefingT(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestBriefingT, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='briefingt', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='briefingt', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('briefingt')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_primary_key_commas(self):
        """
        Commas in primary keys should error
        """
        record = get_chromo('briefingt')['examples']['record'].copy()
        record['tracking_number'] = 'this,is,a,failure'
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'tracking_number' in err['records'][0]
        assert err['records'][0]['tracking_number'] == ['Comma is not allowed in Briefing Note Number field']

    def test_blank(self):
        """
        Should raise a Database key error
        """
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'tracking_number' in err['key'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception
        """
        chromo = get_chromo('briefingt')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['title_en', 'title_fr',
                                    'originating_sector_en', 'originating_sector_fr',
                                    'addressee', 'date_received',
                                    'action_required']

        for field in chromo['fields']:
            if field['datastore_id'] in chromo['datastore_primary_key']:
                continue
            if field.get('excel_required') or field.get('form_required'):
                assert field['datastore_id'] in expected_required_fields
                record[field['datastore_id']] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

    def test_duolang_fields(self):
        """
        Fields with both _en and _fr should require eachother
        """
        chromo = get_chromo('briefingt')
        record = chromo['examples']['record'].copy()

        # >= 2026-02-01
        record['date_received'] = '2026-02-01'

        record['additional_information_en'] = 'Not Blank'
        record['additional_information_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'additional_information_fr' in err['records'][0]

        record['additional_information_fr'] = 'Not Blank'
        record['additional_information_en'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'additional_information_en' in err['records'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('briefingt')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['addressee', 'action_required']

        for field in chromo['fields']:
            if field.get('published_resource_computed_field'):
                continue
            if 'choices_file' in field or 'choices' in field:
                assert field['datastore_id'] in expected_choice_fields
                if field['datastore_type'] == '_text':
                    record[field['datastore_id']] = ['zzz']
                else:
                    record[field['datastore_id']] = 'zzz'

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for expected_choice_field in expected_choice_fields:
            assert expected_choice_field in err['records'][0]

    def test_filter_script(self):
        """
        Filter out default Registry fields.

        NOTE: csv.DictReader treats every dict value as a string,
              so we need to use Strings here. Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        record = get_chromo('briefingt')['examples']['record'].copy()

        # filters out record_created, record_modified, user_modified
        record['record_created'] = 'Not Blank'
        record['record_modified'] = 'Not Blank'
        record['user_modified'] = 'Not Blank'

        test_record = filter_generic.test(dict(record))
        assert 'record_created' not in test_record
        assert 'record_modified' not in test_record
        assert 'user_modified' not in test_record


class TestBriefingTNil(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestBriefingTNil, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='briefingt', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='briefingt', owner_org=org['name'])

        self.resource_id = rval['resources'][1]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('briefingt-nil')['examples']['record'].copy()
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])

    def test_blank(self):
        """
        Should raise a Database key error
        """
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'key' in err
        assert 'year, month' in err['key'][0]

    def test_date_constraints(self):
        """
        Should not be able to input unsupported years and months
        """
        record = get_chromo('briefingt-nil')['examples']['record'].copy()

        # cannot be after current year
        record['year'] = 2999
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'year' in err['records'][0]
        assert err['records'][0]['year'] == ['This must list the year you are reporting on (not the fiscal year).']

        # month has to be between 1-12
        record['year'] = 2012
        record['month'] = 0
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'month' in err['records'][0]
        assert err['records'][0]['month'] == ['Please enter a month number from 1-12']

        record['month'] = 13
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'month' in err['records'][0]
        assert err['records'][0]['month'] == ['Please enter a month number from 1-12']
