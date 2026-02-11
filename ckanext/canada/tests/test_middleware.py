# -*- coding: UTF-8 -*-
from ckanext.canada.tests import (
    CanadaTestBase,
    mock_is_registry_domain
)
from ckan.plugins.toolkit import h, g, request
from ckanext.canada.tests.factories import (
    CanadaSysadminWithToken as Sysadmin,
    CanadaOrganization as Organization,
    CanadaDataset as Dataset,
    CanadaResource as Resource
)
from ckan.tests.helpers import change_config

import re
import flask
from urllib.parse import urlparse
from ckan import model
from ckan.views.api import _finish_ok

import pytest
import mock


def _get_relative_offset_from_response(response):
    assert response.headers
    assert 'Location' in response.headers
    return urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()


@pytest.mark.usefixtures('with_request_context')
class TestCanadaMiddleware(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestCanadaMiddleware, self).setup_class()

        self.sysadmin = Sysadmin()
        self.extra_environ_system = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.environ_overrides_system = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_500_error_support_id_generation(self, app):
        """
        Raised, uncaught exceptions inside of the Flask app should
        be proceessed by a middleware's error_handler to set a support ID.

        Formatted as: <numbers in system hostname>-<epoch time>
        """
        @app.flask_app.route('/_test')
        def _test():
            raise Exception

        app.get('/_test', extra_environ=self.extra_environ_system, status=500)

        assert 'ERROR_SUPPORT_ID' in g
        assert re.match(r'^\d+-\d+.\d+$', g.ERROR_SUPPORT_ID) is not None

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_log_extra_header(self, app):
        """
        All requests should set an X-LogExtra header for authenticated users.

        This should always include user=<user_name>

        This also includes org={o} type={t} id={i} rid={r} for API POST requests.

        It should log for all versions of the API, also excluding a version number.
        """
        current_user = model.User.get(self.sysadmin['name'])
        org = Organization()
        pkg = Dataset(owner_org=org['name'])
        res = Resource(package_id=pkg['id'])

        @app.flask_app.route('/_test')
        def _test():
            return _finish_ok({})

        # logged out users do not have log extras
        get_response = app.get('/_test')
        assert 'X-LogExtra' not in get_response.headers

        with mock.patch('ckan.lib.helpers.current_user', current_user):
            flask.g.user = self.sysadmin['name']
            for i in range(0, 4):
                # resource_id in data will output rid in log extras
                offset = '/api/%s/action/resource_patch' % i
                if i == 0:
                    offset = '/api/action/resource_patch'
                response = app.post(
                    offset,
                    data={
                        'id': res['id'],
                        'resource_id': res['id'],
                        'name_translated-en': 'UPDATED DESCRIPTION %s' % i,
                        'name_translated-fr': 'UPDATED DESCRIPTION %s' % i,
                    },
                    extra_environ=self.extra_environ_system,
                    environ_overrides=self.environ_overrides_system,
                    follow_redirects=True)

                expected_header = 'user=%s org=%s type=%s id=%s rid=%s' % \
                    (self.sysadmin['name'], org['name'], pkg['type'], pkg['id'], res['id'])

                assert 'X-LogExtra' in response.headers
                assert response.headers['X-LogExtra'] == expected_header

            for i in range(0, 4):
                # no resource_id in data will NOT output rid in log extras
                offset = '/api/%s/action/resource_patch' % i
                if i == 0:
                    offset = '/api/action/resource_patch'
                response = app.post(
                    offset,
                    data={
                        'id': res['id'],
                        'name_translated-en': 'UPDATED DESCRIPTION %s' % i,
                        'name_translated-fr': 'UPDATED DESCRIPTION %s' % i,
                    },
                    extra_environ=self.extra_environ_system,
                    environ_overrides=self.environ_overrides_system,
                    follow_redirects=True)

                expected_header = 'user=%s org=%s type=%s id=%s' % \
                    (self.sysadmin['name'], org['name'], pkg['type'], pkg['id'])

                assert 'X-LogExtra' in response.headers
                assert response.headers['X-LogExtra'] == expected_header

            # non-API requests will just include username
            get_response = app.get('/_test', extra_environ=self.extra_environ_system,
                                   environ_overrides=self.environ_overrides_system)

            assert 'X-LogExtra' in get_response.headers
            assert get_response.headers['X-LogExtra'] == 'user=%s' % self.sysadmin['name']

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    @change_config('ckanext.canada.disable_content_security_policy', False)
    @change_config('ckanext.canada.content_security_policy', "Content-Security-Policy: default-src 'self' 'nonce-[[NONCE]]';")
    def test_nonce_generation(self, app):
        """
        All requests should generate a CSP_NONCE into the app environ.

        It should also set a Content-Security-Policy header, replacing [[NONCE]]
        in the value of the ckanext.canada.content_security_policy config option.
        """
        @app.flask_app.route('/_test')
        def _test():
            # cannot get request.environ after we get the response.
            # send the environ value back as the response data.
            return _finish_ok({'nonce': request.environ.get('CSP_NONCE')})

        response = app.get('/_test', extra_environ=self.extra_environ_system, status=200)
        nonce_value = response.get_json()['nonce']

        assert 'Content-Security-Policy' in response.headers
        assert 'nonce-%s' % nonce_value in response.headers['Content-Security-Policy']
