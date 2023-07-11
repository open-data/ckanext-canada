# -*- coding: UTF-8 -*-
from ckan.plugins.toolkit import h
from ckanapi import LocalCKAN

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import CanadaOrganization as Organization
from ckan.tests.helpers import FunctionalTestBase


class TestPackageAlerts(FunctionalTestBase):
    def setup(self):
        super(TestPackageAlerts, self).setup()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.app = self._get_test_app()
        self.sysadmin_action = LocalCKAN(
            username=self.sysadmin['name']).action


    def test_marked_not_eady_to_publish(self):
        data = self.filled_dataset_data()
        data['imso_approval'] = 'false'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef0', **data)

        offset = h.url_for(controller='package',
                           action='read',
                           id='12345678-9abc-def0-1234-56789abcdef0')
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response
        assert 'Approval required' in response


    def test_approval_required(self):
        data = self.filled_dataset_data()
        data['ready_to_publish'] = 'false'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef1', **data)

        offset = h.url_for(controller='package',
                           action='read',
                           id='12345678-9abc-def0-1234-56789abcdef1')
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response
        assert 'Record marked not ready to publish' in response

        data['imso_approval'] = 'false'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef2', **data)

        offset = h.url_for(controller='package',
                           action='read',
                           id='12345678-9abc-def0-1234-56789abcdef2')
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response
        assert 'Record marked not ready to publish' in response


    def test_queued_for_publishing(self):
        data = self.filled_dataset_data()
        data['imso_approval'] = 'true'
        data['ready_to_publish'] = 'true'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef3', **data)

        offset = h.url_for(controller='package',
                           action='read',
                           id='12345678-9abc-def0-1234-56789abcdef3')
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'View on Portal' in response
        assert 'Queued for publishing' in response


    def test_view_on_portal(self):
        data = self.filled_dataset_data()
        data['imso_approval'] = 'true'
        data['ready_to_publish'] = 'true'
        data['portal_release_date'] = '2023-07-07'
        self.sysadmin_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef4', **data)

        offset = h.url_for(controller='package',
                           action='read',
                           id='12345678-9abc-def0-1234-56789abcdef4')
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert 'View on Portal' in response
        assert not 'Queued for publishing' in response
        assert not 'Approval required' in response
        assert not 'Record marked not ready to publish' in response


    def filled_dataset_data(self):
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
