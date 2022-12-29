# -*- coding: UTF-8 -*-
from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import User
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckan.model import Session
from ckanapi import LocalCKAN, ValidationError
from nose.tools import assert_raises

SIMPLE_SUGGESTION = {
    'type': 'prop',
    'title_translated': {
        'en': u'Simple Suggestion',
        'fr': u'Suggestion simple'
    },
    'notes_translated': {
        'en': u'Notes',
        'fr': u'Notes',
    },
    'keywords': {
        'en': [u'key'],
        'fr': [u'clé'],
    },
    'reason': 'personal_interest',
    'subject': ['persons'],
    'date_submitted': '2021-01-01',
    'date_forwarded': '2021-02-01',

    'status': [],
}

COMPLETE_SUGGESTION = dict(SIMPLE_SUGGESTION,
    status=[
        {
            'date': '2021-03-01',
            'reason': 'under_review',
            'comments': {
                'en': 'good idea',
                'fr': 'bon idée',
            },
        },
    ]
)

UPDATED_SUGGESTION = dict(SIMPLE_SUGGESTION,
    status=[
        {
            'date': '2021-04-01',
            'reason': 'released',
            'comments': {
                'en': 'here',
                'fr': 'ici',
            },
        },
        {
            'date': '2021-03-01',
            'reason': 'under_review',
            'comments': {
                'en': 'good idea',
                'fr': 'bon idée',
            },
        },
    ]
)


class TestSuggestedDataset(FunctionalTestBase):
    def setup(self):
        super(TestSuggestedDataset, self).setup()
        user = User()
        self.slc = LocalCKAN()
        self.ulc = LocalCKAN(username=user['name'])
        self.simple_org = Organization()
        self.editor_org = Organization(users=[{
                    'name': user['name'],
                    'capacity': 'editor'}])


    def test_simple_suggestion(self):
        resp = self.slc.action.package_create(
            owner_org=self.simple_org['name'],
            **SIMPLE_SUGGESTION)

        assert 'status' not in resp


    def test_normal_user_cant_create(self):
        assert_raises(ValidationError,
            self.ulc.action.package_create,
            owner_org=self.editor_org['name'],
            **SIMPLE_SUGGESTION)


    def test_normal_user_can_update(self):
        resp = self.slc.action.package_create(
            owner_org=self.editor_org['name'],
            **SIMPLE_SUGGESTION)
        resp = self.ulc.action.package_update(
            owner_org=self.editor_org['name'],
            id=resp['id'],
            **COMPLETE_SUGGESTION)

        assert resp['status'][0]['reason'] == 'under_review'


    def test_responses_ordered(self):
        resp = self.slc.action.package_create(
            owner_org=self.simple_org['name'],
            **UPDATED_SUGGESTION)

        # first update will be moved to end based on date field
        assert resp['status'][1]['reason'] == 'released'

