# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)

import pytest

from ckanapi import LocalCKAN, ValidationError, NotAuthorized

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
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestSuggestedDataset, self).setup_method()

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
        with pytest.raises(NotAuthorized) as e:
            self.member_lc.action.package_create(
                owner_org=self.org['name'],
                **SIMPLE_SUGGESTION)
        err = str(e.value)
        assert 'not authorized to add dataset' in err or \
               'not authorized to create packages' in err


    def test_normal_user_cant_update(self):
        "Member users cannot update suggested datasets"
        response = self.system_lc.action.package_create(
            owner_org=self.org['name'],
            **SIMPLE_SUGGESTION)

        with pytest.raises(NotAuthorized) as e:
            self.member_lc.action.package_update(
                owner_org=self.org['name'],
                id=response['id'],
                **COMPLETE_SUGGESTION)
        err = str(e.value)
        assert 'not authorized to edit package' in err


    def test_editor_user_cant_create(self):
        "Editor users cannot create suggested datasets"
        with pytest.raises(ValidationError) as ve:
            self.editor_lc.action.package_create(
                owner_org=self.org['name'],
                **SIMPLE_SUGGESTION)
        err = ve.value.error_dict
        for e in err:
            assert [m for m in err[e] if 'Only sysadmin may set this value' in m]


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
