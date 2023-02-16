# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo


class TestConsultations(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()

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
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[{}])
        err = ve.value.error_dict
        assert 'key' in err
        assert 'registration_number' in err['key'][0]


    def test_multiple_errors(self):
        with pytest.raises(ValidationError) as ve:
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


    def test_not_going_forward_unpublished(self):
        record = get_chromo('consultations')['examples']['record']
        with pytest.raises(ValidationError) as ve:
            self.lc.action.datastore_upsert(
                resource_id=self.resource_id,
                records=[dict(record, publishable='Y', status='NF')])
        err = ve.value.error_dict
        assert 'records' in err
        assert 'status' in err['records'][0]
