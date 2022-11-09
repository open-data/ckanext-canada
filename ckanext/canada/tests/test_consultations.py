# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo

import logging
log = logging.getLogger(__name__)


class TestConsultations(object):
    @classmethod
    def setup_class(self):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()

        log.info('Running setup for {}'.format(self.__name__))

        org = Organization()
        lc = LocalCKAN()

        log.info('Creating organization with id: {}'.format(org['name']))
        log.info('Setting organization dataset type to {}'.format('consultations'))

        lc.action.recombinant_create(dataset_type='consultations', owner_org=org['name'])
        rval = lc.action.recombinant_show(dataset_type='consultations', owner_org=org['name'])

        self.resource_id = rval['resources'][0]['id']


    def test_blank(self):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        expected = {}
        #TODO: assert the expected error
        assert ve is not None


    def test_multiple_errors(self):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
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
        err = ve.value.error_dict['records'][0]
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
            assert k in err
            assert err[k] == expected[k]


    def test_example(self):
        lc = LocalCKAN()
        record = get_chromo('consultations')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=self.resource_id,
            records=[record])


    def test_not_going_forward_unpublished(self):
        lc = LocalCKAN()
        record = get_chromo('consultations')['examples']['record']
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[dict(record, publishable='Y', status='NF')])
        err = ve.value.error_dict['records'][0]
        expected = {
            u'status': [u'If Status is set to: Not Going Forward, Publish Record must be set to No']
            }
        assert err == expected
