# -*- coding: UTF-8 -*-
import pytest
from urlparse import urlparse
from ckan.lib.helpers import url_for

from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import CanadaOrganization as Organization


@pytest.mark.usefixtures('with_request_context')
class TestWebForms(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.dataset_id = 'f3e4adb9-6e32-4cb4-bf68-1eab9d1288f4'
        self.resource_id = '8b29e2c6-8a12-4537-bf97-fe4e5f0a14c1'


    def test_new_dataset_required_fields(self, app):
        offset = url_for('dataset.new')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Create Dataset' in response.body
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        response = app.post(offset,
                            data=self._filled_dataset_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=False)

        offset = self._get_offset_from_response(response)
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Add data to the dataset' in response.body

        response = app.post(offset,
                            data=self._filled_resource_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=True)

        assert 'Resource added' in response.body


    def test_new_dataset_missing_fields(self, app):
        offset = url_for('dataset.new')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Create Dataset' in response.body
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        incomplete_dataset_form = {
            'id': self.dataset_id,
            'save': '',
            '_ckan_phase': '1'
        }
        response = app.post(offset,
                            data=incomplete_dataset_form,
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=True)

        assert 'Errors in form' in response.body
        assert 'Title (French):' in response.body
        assert 'Publisher - Current Organization Name:' in response.body
        assert 'Subject:' in response.body
        assert 'Title (English):' in response.body
        assert 'Description (English):' in response.body
        assert 'Description (French):' in response.body
        assert 'Keywords (English):' in response.body
        assert 'Keywords (French):' in response.body
        assert 'Date Published:' in response.body
        assert 'Frequency:' in response.body
        assert 'Approval:' in response.body
        assert 'Date Published:' in response.body
        assert 'Ready to Publish:' in response.body

        response = app.post(offset,
                            data=self._filled_dataset_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=False)

        offset = self._get_offset_from_response(response)
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Add data to the dataset' in response.body

        incomplete_resource_form = {
            'id': '',
            'package_id': self.dataset_id,
            'url': 'somewhere',
            'save': 'go-dataset-complete'
        }
        response = app.post(offset,
                            data=incomplete_resource_form,
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=True)

        assert 'Errors in form' in response.body
        assert 'Title (English):' in response.body
        assert 'Title (French):' in response.body
        assert 'Resource Type:' in response.body
        assert 'Format:' in response.body


    def _filled_dataset_form(self):
        return {
            'id': self.dataset_id,
            'owner_org': self.org['id'],
            'collection': 'primary',
            'title_translated-en': 'english title',
            'title_translated-fr': 'french title',
            'notes_translated-en': 'english description',
            'notes_translated-fr': 'french description',
            'subject': 'arts_music_literature',
            'keywords-en': 'english keywords',
            'keywords-fr' : 'french keywords',
            'date_published': '2000-01-01',
            'ready_to_publish': 'false',
            'frequency': 'as_needed',
            'jurisdiction': 'federal',
            'license_id': 'ca-ogl-lgo',
            'restrictions': 'unrestricted',
            'imso_approval': 'true',
            'save': '',
            '_ckan_phase': '1'
        }


    def _filled_resource_form(self):
        return {
            'id': '',
            'package_id': self.dataset_id,
            'name_translated-en': 'english resource name',
            'name_translated-fr': 'french resource name',
            'resource_type': 'dataset',
            'url': 'somewhere',
            'format': 'CSV',
            'language': 'en',
            'save': 'go-dataset-complete'
        }


    def _get_offset_from_response(self, response):
        assert response.headers
        assert 'Location' in response.headers
        return urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()
