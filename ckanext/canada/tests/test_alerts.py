# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckan.plugins.toolkit import h
from ckanapi import LocalCKAN

import pytest
from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import CanadaOrganization as Organization


@pytest.mark.usefixtures('with_request_context')
class TestPackageAlerts(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestPackageAlerts, self).setup_method(method)

        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.sysadmin_action = LocalCKAN(
            username=self.sysadmin['name']).action


    def test_marked_not_eady_to_publish(self, app):
        data = self._filled_dataset_data()
        data['imso_approval'] = 'false'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef0', **data)

        offset = h.url_for('dataset.read',
                           id='12345678-9abc-def0-1234-56789abcdef0')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response.body
        assert 'Seek out departmental approval and mark as approved to continue' in response.body


    def test_approval_required(self, app):
        data = self._filled_dataset_data()
        data['ready_to_publish'] = 'false'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef1', **data)

        offset = h.url_for('dataset.read',
                           id='12345678-9abc-def0-1234-56789abcdef1')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response.body
        assert 'Draft record has been saved and can be edited. Mark as ready to publish to continue' in response.body


    def test_queued_for_publishing(self, app):
        data = self._filled_dataset_data()
        data['imso_approval'] = 'true'
        data['ready_to_publish'] = 'true'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef3', **data)

        offset = h.url_for('dataset.read',
                           id='12345678-9abc-def0-1234-56789abcdef3')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response.body
        assert 'Data record is in queue for validation' in response.body
        assert 'Record will be published by the following business day upon validation' in response.body


    def test_view_on_portal(self, app):
        data = self._filled_dataset_data()
        data['imso_approval'] = 'true'
        data['ready_to_publish'] = 'true'
        data['portal_release_date'] = '2023-07-07'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef4', **data)

        offset = h.url_for('dataset.read',
                           id='12345678-9abc-def0-1234-56789abcdef4')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert 'View on Portal' in response.body
        assert not 'Data record is in queue for validation' in response.body
        assert not 'Record will be published by the following business day upon validation' in response.body
        assert not 'Seek out departmental approval and mark as approved to continue' in response.body
        assert not 'Draft record has been saved and can be edited. Mark as ready to publish to continue' in response.body


    def _filled_dataset_data(self):
        # type: () -> dict
        return {
            'type': 'dataset',
            'collection': 'primary',
            'title_translated': {'en': u'A Novel By Tolstoy'},
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
            'jurisdiction': 'federal',
            'maintainer_email': 'not@all.example.com',
            'restrictions': 'unrestricted',
            'resources': [{
                'name_translated': {'en': u'Full text.', 'fr': u'Full text.'},
                'format': u'TXT',
                'url': u'http://www.annakarenina.com/download/',
                'size': 42,
                'resource_type': 'dataset',
                'language': ['zxx'],
            }],
            'owner_org': self.org['name'],
            'title_translated': {
                'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            'frequency': 'as_needed',
            'notes_translated': {'en': u'...', 'fr': u'...'},
            'subject': [u'persons'],
            'date_published': u'2013-01-01',
            'keywords': {'en': [u'book'], 'fr': [u'livre']},
        }
