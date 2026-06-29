# -*- coding: UTF-8 -*-
from ckanext.canada.tests import (
    CanadaTestBase,
    mock_is_registry_domain,
    mock_is_portal_domain,
    get_test_domains
)
import pytest
import mock
from ckan.plugins.toolkit import h

from ckan.tests.helpers import CKANResponse  # noqa: F401

from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaSysadminWithToken as Sysadmin
)
# type_ignore_reason: custom fixtures
from ckanext.canada.tests.fixtures import (  # noqa: F401
    strip_lang_prefix_app  # type: ignore
)
from ckanext.canada.tests.helpers import get_relative_offset_from_response


@pytest.mark.usefixtures('with_request_context')
@pytest.mark.usefixtures('strip_lang_prefix_app')
class TestDomainMap(CanadaTestBase):
    """
    Tests for expected behaviour with the language_domains plugin.

    IMPORTANT: the Portal nginx for /data/ does rewrite /data/(.*) /$1
               which we cannot mock a reverse proxy here. Just do not
               include the /data/ in the offset for the requests.

    IMORTANT: with_request_context does not set CKAN_LANG, so we have to
              set it. E.g. if doing a /fr/ request set CKAN_LANG=fr
    """
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestDomainMap, self).setup_class()
        self.test_domain_map = get_test_domains()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester_registry = {'Authorization': self.sysadmin['token'],
                                              'HTTP_HOST': self.test_domain_map['registry']['en'],
                                              'CKAN_LANG': 'en'}
        self.extra_environ_tester_portal_en = {'Authorization': self.sysadmin['token'],
                                               'HTTP_HOST': self.test_domain_map['portal']['en'],
                                               'CKAN_LANG': 'en'}
        self.extra_environ_tester_portal_fr = {'Authorization': self.sysadmin['token'],
                                               'HTTP_HOST': self.test_domain_map['portal']['fr'],
                                               'CKAN_LANG': 'fr'}
        self.environ_overrides_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization(users=[{
            'name': self.sysadmin['name'],
            'capacity': 'admin'}])

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_registry_base_redirect(self, app):
        """
        Requesting base dir should redirect to /en
        """
        offset = '/user/login'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=301,
                           follow_redirects=False)  # catch redirect

        offset, host = get_relative_offset_from_response(response)
        assert offset == '/en/user/login'
        assert host == self.test_domain_map['registry']['en']

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_base_redirect(self, app):
        """
        Requesting base dir should redirect to /data/en
        """
        offset = '/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=301,
                           follow_redirects=False)  # catch redirect

        offset, host = get_relative_offset_from_response(response)
        assert offset == '/data/en/organization'
        assert host == self.test_domain_map['portal']['en']

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_domain_redirect(self, app):
        """
        Requesting a /fr page from the English domain should
        redirect to the French domain, and vice versa
        """
        # english domain to french domain
        offset = '/fr/organization'
        response = app.get(offset, extra_environ=dict(self.extra_environ_tester_portal_en, CKAN_LANG='fr'),
                           environ_overrides=self.environ_overrides_tester,
                           status=301,
                           follow_redirects=False)  # catch redirect

        offset, host = get_relative_offset_from_response(response)
        assert offset == '/data/fr/organization'
        assert host == self.test_domain_map['portal']['fr']

        # french domain to english domain
        offset = '/en/organization'
        response = app.get(offset, extra_environ=dict(self.extra_environ_tester_portal_fr, CKAN_LANG='en'),
                           environ_overrides=self.environ_overrides_tester,
                           status=301,
                           follow_redirects=False)  # catch redirect

        offset, host = get_relative_offset_from_response(response)
        assert offset == '/data/en/organization'
        assert host == self.test_domain_map['portal']['en']

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_registry_no_redirect(self, app):
        """
        Requesting the correct language and domain should not do a redirect
        """
        offset = '/en/dataset/'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           follow_redirects=False)  # no need for redirects

        print('    ')
        print('DEBUGGING::')
        print('    ')
        print(response.body)
        print(response.headers)
        print('    ')
        assert False

        # english request
        offset = '/en/user/login'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        assert 'Forgotten your password?' in response.body
        assert '/fr/user/login' in response.body

        # french request
        offset = '/fr/user/login'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        assert 'Forgotten your password?' in response.body
        assert '/en/user/login' in response.body
