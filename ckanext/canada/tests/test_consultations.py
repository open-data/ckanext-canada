# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN, ValidationError

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resources

from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{'dataset_type': 'consultations'}],
    indirect=True)
class TestConsultations(object):
    def test_example(self, request):
        lc = LocalCKAN()
        record = get_chromo('consultations')['examples']['record']
        lc.action.datastore_upsert(
            resource_id=request.config.cache.get("resource_id", None),
            records=[record])


    def test_blank(self, request):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[{}])
        assert ve is not None


    def test_multiple_errors(self, request):
        lc = LocalCKAN()
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
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


    def test_not_going_forward_unpublished(self, request):
        lc = LocalCKAN()
        record = get_chromo('consultations')['examples']['record']
        with pytest.raises(ValidationError) as ve:
            lc.action.datastore_upsert(
                resource_id=request.config.cache.get("resource_id", None),
                records=[dict(record, publishable='Y', status='NF')])
        err = ve.value.error_dict['records'][0]
        expected = {
            u'status': [u'If Status is set to: Not Going Forward, Publish Record must be set to No']
            }
        assert err == expected
