# -*- coding: UTF-8 -*-
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo
from ckanext.canada.tests import canada_tests_init_validation


class TestConsultations(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestConsultations, self).setup()
        org = Organization()
        self.lc = LocalCKAN()
        self.lc.action.recombinant_create(dataset_type='consultations', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='consultations', owner_org=org['name'])
        self.resource_id = rval['resources'][0]['id']


    def test_example(self):
        record = get_chromo('consultations')['examples']['record']
        self.lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_blank(self):
        assert_raises(ValidationError,
            self.lc.action.datastore_upsert,
            resource_id=self.resource_id,
            records=[{}])


    def test_multiple_errors(self):
        with assert_raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{
                    'registration_number': 'CCC0249',
                    'publishable': 'Q',
                    'subjects': ["IP", "CD", "HS", "GEO", "SE", "MATH"],
                    'title_fr': u'seulment français',
                    'description_en': 'only english',
                    'target_participants_and_audience': ["ZOMBIES", "IP", "IG", "PT"],
                    'end_date': "2018-05-15",
                    'status': 'P',
                    'profile_page_en': 'http://example.gc.ca/en',
                    'profile_page_fr': 'http://example.gc.ca/fr',
                    'partner_departments': ["D271", "DARN", "D141"],
                    'policy_program_lead_email': 'program.lead@example.gc.ca',
                    'high_profile': "Y",
                    'report_available_online': "N",
                    }])
        err = ve.exception.error_dict['records'][0]
        expected = {
            'publishable': ['Invalid choice: "Q"'],
            'subjects': ['Invalid choice: "GEO,MATH"'],
            'title_en': ['This field must not be empty'],
            'description_fr': ['This field must not be empty'],
            'target_participants_and_audience': ['Invalid choice: "ZOMBIES"'],
            'start_date': ['This field must not be empty'],
            'partner_departments': ['Invalid choice: "DARN"'],
            'rationale': ['This field must not be empty'],
            }
        for k in set(err) | set(expected):
            assert_equal(err.get(k), expected.get(k), (k, err))


    def test_not_going_forward_unpublished(self):
        record = get_chromo('consultations')['examples']['record']
        with assert_raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[dict(record, publishable='Y', status='NF')])
        err = ve.exception.error_dict['records'][0]
        expected = {
            u'status': [u'If Status is set to: Not Going Forward, Publish Record must be set to No']
            }
        assert_equal(err, expected)

