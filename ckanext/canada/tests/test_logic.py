# -*- coding: UTF-8 -*-
import pytest
import mock

from ckanext.canada.tests import CanadaTestBase
from ckanapi import LocalCKAN
from ckan.plugins.toolkit import h

from ckanext.canada.tests.factories import (
    CanadaResource as Resource,
    mock_isfile,
    mock_open_ip_list,
    MOCK_IP_ADDRESS,
)


class TestCanadaLogic(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestCanadaLogic, self).setup_method(method)

        self.lc = LocalCKAN()

    def test_data_dictionary(self):
        """
        The custom fields should get saved in the Data Dictionary,
        and be returned from datastore_info.
        """
        resource = Resource()
        self.lc.action.datastore_create(resource_id=resource['id'],
                                        force=True,
                                        fields=[{'id': 'exampled_id',
                                                 'type': 'text',
                                                 'info': {'label_en': 'Example Label',
                                                          'label_fr': 'Example Label FR',
                                                          'notes_en': 'Example Description',
                                                          'notes_fr': 'Example Description FR'}}])

        ds_info = self.lc.action.datastore_info(id=resource['id'])

        assert 'fields' in ds_info
        assert len(ds_info['fields']) == 1
        assert ds_info['fields'][0]['id'] == 'exampled_id'
        assert 'info' in ds_info['fields'][0]
        assert 'label_en' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['label_en'] == 'Example Label'
        assert 'label_fr' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['label_fr'] == 'Example Label FR'
        assert 'notes_en' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['notes_en'] == 'Example Description'
        assert 'notes_fr' in ds_info['fields'][0]['info']
        assert ds_info['fields'][0]['info']['notes_fr'] == 'Example Description FR'


@pytest.mark.usefixtures('with_request_context')
class TestPublicRegistry(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestPublicRegistry, self).setup_method(method)
        self.extra_environ_tester = {'REMOTE_USER': str(u""), 'REMOTE_ADDR': MOCK_IP_ADDRESS}
        self.extra_environ_tester_bad_ip = {'REMOTE_USER': str(u""), 'REMOTE_ADDR': '174.116.80.142'}

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    def test_register_bad_ip_address(self, app):
        offset = h.url_for('user.register')
        response = app.get(offset, extra_environ=self.extra_environ_tester_bad_ip)

        assert response.status_code == 403

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    def test_register_good_ip_address(self, app):
        offset = h.url_for('user.register')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert response.status_code == 200

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    @pytest.mark.skip(reason="No mock for repoze handler in tests")
    def test_login_bad_ip_address(self, app):
        offset = h.url_for('canada.login')
        response = app.get(offset, extra_environ=self.extra_environ_tester_bad_ip)
        #FIXME: repoze handler in tests
        assert response.status_code == 403

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    @pytest.mark.skip(reason="No mock for repoze handler in tests")
    def test_login_good_ip_address(self, app):
        offset = h.url_for('canada.login')
        response = app.get(offset, extra_environ=self.extra_environ_tester)
        #FIXME: repoze handler in tests
        assert response.status_code == 200

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    def test_api_bad_ip_address(self, app):
        offset = h.url_for('api.action', logic_function='status_show')
        response = app.get(offset, extra_environ=self.extra_environ_tester_bad_ip)

        assert response.status_code == 403

    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('__builtin__.open', mock_open_ip_list)
    def test_api_good_ip_address(self, app):
        offset = h.url_for('api.action', logic_function='status_show')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert response.status_code == 200
