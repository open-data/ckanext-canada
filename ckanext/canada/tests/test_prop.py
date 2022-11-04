# -*- coding: UTF-8 -*-
from ckan.tests.helpers import call_action
from ckan.tests import factories
import ckan.lib.search as search
from ckanext.canada.tests.factories import CanadaOrganization as Organization

import pytest

from ckanapi import LocalCKAN, ValidationError
import json
from nose.tools import assert_raises, assert_equal

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

@pytest.mark.usefixtures('clean_db')
class TestSuggestedDataset(object):

    def test_simple_suggestion(self):
        lc = LocalCKAN()
        org = Organization()
        resp = lc.action.package_create(
            owner_org=org['name'],
            **SIMPLE_SUGGESTION)

        assert 'status' not in resp

    def test_normal_user_cant_create(self):
        user = factories.User()
        lc = LocalCKAN(username=user['name'])
        org = Organization(users=[
                {
                    'name': user['name'],
                    'capacity': 'editor',
                }
            ]
        )
        assert_raises(ValidationError,
            lc.action.package_create,
            owner_org=org['name'],
            **SIMPLE_SUGGESTION)

    def test_normal_user_can_update(self):
        user = factories.User()
        slc = LocalCKAN()
        ulc = LocalCKAN(username=user['name'])
        org = Organization(users=[
                {
                    'name': user['name'],
                    'capacity': 'editor',
                }
            ]
        )
        resp = slc.action.package_create(
            owner_org=org['name'],
            **SIMPLE_SUGGESTION)
        resp = ulc.action.package_update(
            owner_org=org['name'],
            id=resp['id'],
            **COMPLETE_SUGGESTION)

        assert resp['status'][0]['reason'] == 'under_review'

    def test_responses_ordered(self):
        lc = LocalCKAN()
        org = Organization()
        resp = lc.action.package_create(
            owner_org=org['name'],
            **UPDATED_SUGGESTION)

        # first update will be moved to end based on date field
        assert resp['status'][1]['reason'] == 'released'
