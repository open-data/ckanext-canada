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

filter_nap6_path = os.path.join(os.path.dirname(str(__file__)), '../../../bin/filter/filter_nap6.py')
spec = util.spec_from_file_location("canada.bin.filters.nap6", filter_nap6_path)
filter_nap6 = util.module_from_spec(spec)
sys.modules["canada.bin.filters.nap6"] = filter_nap6
spec.loader.exec_module(filter_nap6)


class TestNap6(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestNap6, self).setup_class()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='nap6', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='nap6', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']

    def test_example(self):
        """
        Example data should load
        """
        record = get_chromo('nap6')['examples']['record'].copy()
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
        assert 'reporting_period, indicators' in err['key'][0]

    def test_required_fields(self):
        """
        Excluding required fields should raise an exception
        """
        chromo = get_chromo('nap6')
        record = chromo['examples']['record'].copy()

        expected_required_fields = ['commitments', 'milestones', 'status',
                                    'indicators', 'progress_en', 'progress_fr']

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

    def test_conditional_fields(self):
        """
        Excluding conditionally required fields should raise an exception
        """
        chromo = get_chromo('nap6')
        record = chromo['examples']['record'].copy()

        # if Status is LP, challenges is required
        expected_required_fields = ['challenges']
        record['status'] = 'LP'
        record['challenges'] = None
        record['challenges_other_en'] = None
        record['challenges_other_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

        # if Status is NS, challenges is required
        expected_required_fields = ['challenges']
        record['status'] = 'NS'
        record['challenges'] = None
        record['challenges_other_en'] = None
        record['challenges_other_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        for required_field in expected_required_fields:
            assert required_field in err['records'][0]

        # if challenges is OT, challenges_other_* is required
        expected_required_fields = ['challenges_other_en',
                                    'challenges_other_fr']
        record['status'] = 'NS'
        record['challenges'] = ['OT']
        record['challenges_other_en'] = None
        record['challenges_other_fr'] = None

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
        chromo = get_chromo('nap6')
        record = chromo['examples']['record'].copy()

        record['evidence_en'] = 'Not Blank'
        record['evidence_fr'] = None

        record['challenges_other_en'] = 'Not Blank'
        record['challenges_other_fr'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'evidence_fr' in err['records'][0]
        assert 'challenges_other_fr' in err['records'][0]

        record['evidence_fr'] = 'Not Blank'
        record['evidence_en'] = None

        record['challenges_other_fr'] = 'Not Blank'
        record['challenges_other_en'] = None

        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[record])
        model.Session.rollback()
        err = ve.value.error_dict
        assert 'records' in err
        assert 'evidence_en' in err['records'][0]
        assert 'challenges_other_en' in err['records'][0]

    def test_choice_fields(self):
        """
        Fields with choices should expect those values
        """
        chromo = get_chromo('nap6')
        record = chromo['examples']['record'].copy()

        expected_choice_fields = ['reporting_period', 'commitments', 'milestones',
                                  'indicators', 'status', 'challenges']

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
        Expanding the key/values from the indicators choices
        should result correctly for the required Business Logic

        NOTE: csv.DictReader treats every dict value as a string.
              Empty strings ("") is None.

        NOTE: the filter test returns a Dict, not a csv.DictWriter,
              so we can assert on object types here.
        """
        chromo = get_chromo('nap6')
        record = chromo['examples']['record'].copy()

        indicators_choices = {}
        for field in chromo['fields']:
            if field['datastore_id'] == 'indicators':
                indicators_choices = field['choices']
                break

        for indicator_value, indicator_obj in indicators_choices.items():
            record['indicators'] = indicator_value
            test_record = filter_nap6.test(dict(record))
            assert test_record['indicator_en'] == indicator_obj['en']
            assert test_record['indicator_fr'] == indicator_obj['fr']
            assert test_record['indicator_deadline_en'] == indicator_obj['deadline']['en']
            assert test_record['indicator_deadline_fr'] == indicator_obj['deadline']['fr']
            if isinstance(indicator_obj['lead_dept'], list):
                indicator_obj['lead_dept'] = ','.join(indicator_obj['lead_dept'])
            assert test_record['indicator_lead_dept'] == indicator_obj['lead_dept']
