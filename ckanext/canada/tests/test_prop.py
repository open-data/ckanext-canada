# -*- coding: UTF-8 -*-
from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User)

from ckanapi import LocalCKAN, ValidationError, NotAuthorized
from nose.tools import assert_raises
from ckanext.canada.tests import CanadaTestBase

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


class TestSuggestedDataset(CanadaTestBase):
    def setup(self):
        super(TestSuggestedDataset, self).setup()
        member = User()
        editor = User()
        sysadmin = Sysadmin()
        self.member_lc = LocalCKAN(username=member['name'])
        self.editor_lc = LocalCKAN(username=editor['name'])
        self.system_lc = LocalCKAN(username=sysadmin['name'])
        self.org = Organization(users=[{
            'name': member['name'],
            'capacity': 'member'},
            {'name': editor['name'],
             'capacity': 'editor'},
            {'name': sysadmin['name'],
             'capacity': 'admin'}])


    def test_simple_suggestion(self):
        "System should be able to create suggested datasets"
        response = self.system_lc.action.package_create(
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)

        assert 'status' not in response


    def test_normal_user_cant_create(self):
        "Member users cannot create suggested datasets"
        assert_raises(NotAuthorized,
            self.member_lc.action.package_create,
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)


    def test_normal_user_cant_update(self):
        "Member users cannot update suggested datasets"
        response = self.system_lc.action.package_create(
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)

        assert_raises(NotAuthorized,
            self.member_lc.action.package_update,
            owner_org=self.org['name'],
            id=response['id'],
            **COMPLETE_SUGGESTION)


    def test_editor_user_cant_create(self):
        "Editor users cannot create suggested datasets"
        assert_raises(ValidationError,
            self.editor_lc.action.package_create,
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)


    def test_editor_user_can_update(self):
        "Editors should be able to update suggested datasets"
        response = self.system_lc.action.package_create(
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)

        response = self.editor_lc.action.package_update(
            owner_org=self.org['name'],
            id=response['id'],
            **COMPLETE_SUGGESTION)

        assert response['status'][0]['reason'] == 'under_review'


    def test_responses_ordered(self):
        resp = self.system_lc.action.package_create(
            owner_org=self.org['name'],
            **UPDATED_SUGGESTION)

        # first update will be moved to end based on date field
        assert resp['status'][1]['reason'] == 'released'

