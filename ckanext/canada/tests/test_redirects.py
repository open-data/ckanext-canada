# -*- coding: UTF-8 -*-
import pytest
import mock
from urllib.parse import urlparse

from ckanext.canada.tests import CanadaTestBase, mock_is_registry_domain
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaResource as Resource,
    CanadaSysadminWithToken as Sysadmin
)

from ckanapi import LocalCKAN, ValidationError, NotFound
from ckan.plugins.toolkit import h
from ckanext.recombinant.tables import get_chromo


@pytest.mark.usefixtures('with_request_context')
class TestRedirects(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestRedirects, self).setup_class()

        self.org = Organization(umd_number='example_umd',
                                department_number='example_department')
        self.sysadmin_user = Sysadmin()
        self.action = LocalCKAN(
            username=self.sysadmin_user['name']).action

        self.extra_environ_tester = {'Authorization': self.sysadmin_user['token']}
        self.environ_overrides_tester = {'REMOTE_USER': self.sysadmin_user['name'].encode('ascii')}

        try:
            self._setup_pd(self, type='ati', nil_type='ati-nil')
        except ValidationError as ve:
            if ve.error_dict != {'owner_org': 'dataset type ati already exists for this organization'}:
                raise

    def _setup_pd(self, type, nil_type=None, extra_resource_ids=[]):
        assert type

        self.action.recombinant_create(dataset_type=type, owner_org=self.org['name'])

        rval = self.action.recombinant_show(dataset_type=type, owner_org=self.org['name'])

        chromo = get_chromo(type)

        self.action.datastore_upsert(
            resource_id=rval['resources'][0]['id'],
            records=[chromo['examples']['record']])

        published_pkg_id = None
        if 'published_resource_id' in chromo:
            res = Resource(id=chromo['published_resource_id'])
            published_pkg_id = res.get('package_id')
            self.action.datastore_create(
                resource_id=chromo['published_resource_id'],
                fields=[{'id': 'placeholder', 'type': 'text'}],
                force=True)

        if nil_type:
            nil_chromo = get_chromo(nil_type)

            self.action.datastore_upsert(
                resource_id=rval['resources'][1]['id'],
                records=[nil_chromo['examples']['record']])

            if 'published_resource_id' in nil_chromo:
                if published_pkg_id:
                    Resource(id=nil_chromo['published_resource_id'],
                             package_id=published_pkg_id)
                else:
                    Resource(id=nil_chromo['published_resource_id'])
                self.action.datastore_create(
                    resource_id=nil_chromo['published_resource_id'],
                    fields=[{'id': 'placeholder', 'type': 'text'}],
                    force=True)

        for _id in extra_resource_ids:
            Resource(id=_id)

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_resource_show(self, app):
        """
        Calling resource_show with a Recombinant resource name
        should use the combined published ID.
        """
        ati_chromo = get_chromo('ati')
        ati_nil_chromo = get_chromo('ati-nil')

        res = self.action.resource_show(id='ati')
        assert res['id'] == ati_chromo['published_resource_id']

        res = self.action.resource_show(id='ati-nil')
        assert res['id'] == ati_nil_chromo['published_resource_id']

        with pytest.raises(NotFound):
            self.action.resource_show(id='blurp')

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_package_show(self, app):
        """
        Calling package_show with a Recombinant dataset type
        should use the combined published package ID.
        """
        ati_chromo = get_chromo('ati')
        res = self.action.resource_show(id=ati_chromo['published_resource_id'])
        pkg_id = res['package_id']

        pkg = self.action.package_show(id='ati')
        assert pkg['id'] == pkg_id

        with pytest.raises(NotFound):
            self.action.package_show(id='blurp')

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_datastore_info(self, app):
        """
        Calling datastore_info with a Recombinant resource name
        should use the combined published ID.
        """
        ati_chromo = get_chromo('ati')
        ati_nil_chromo = get_chromo('ati-nil')

        resp = self.action.datastore_info(id='ati')
        assert resp['meta']['id'] == ati_chromo['published_resource_id']

        resp = self.action.datastore_info(id='ati-nil')
        assert resp['meta']['id'] == ati_nil_chromo['published_resource_id']

        with pytest.raises(NotFound):
            self.action.datastore_info(id='blurp')

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_datastore_search(self, app):
        """
        Calling datastore_search with a Recombinant resource name
        should use the combined published ID.
        """
        ati_chromo = get_chromo('ati')
        ati_nil_chromo = get_chromo('ati-nil')

        resp = self.action.datastore_search(resource_id='ati')
        assert resp['resource_id'] == ati_chromo['published_resource_id']

        resp = self.action.datastore_search(resource_id='ati-nil')
        assert resp['resource_id'] == ati_nil_chromo['published_resource_id']

        with pytest.raises(NotFound):
            self.action.datastore_search(resource_id='blurp')

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_package_type_alias(self, app):
        """
        Navigating to /dataset/<recombinant pkg type> should redirect
        to the combined published package page.
        """
        ati_chromo = get_chromo('ati')
        res = self.action.resource_show(id=ati_chromo['published_resource_id'])
        pkg_id = res['package_id']

        response = app.get('/en/dataset/ati',
                           extra_environ=self.extra_environ_tester,
                           environ_overrides=self.environ_overrides_tester,
                           status=302,
                           follow_redirects=False)
        assert response.headers
        assert 'Location' in response.headers
        loc = urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()

        assert loc == '/en/dataset/%s' % pkg_id

        app.get('/en/dataset/blurp',
                extra_environ=self.extra_environ_tester,
                environ_overrides=self.environ_overrides_tester,
                status=404,
                follow_redirects=False)

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_recombinant_resource_name_alias(self, app):
        """
        Navigating to /resource/<recombinant name> should redirect
        to the combined published resource page.
        """
        ati_chromo = get_chromo('ati')
        ati_nil_chromo = get_chromo('ati-nil')
        res = self.action.resource_show(id=ati_chromo['published_resource_id'])
        pkg_id = res['package_id']

        response = app.get('/en/resource/ati',
                           extra_environ=self.extra_environ_tester,
                           environ_overrides=self.environ_overrides_tester,
                           status=302,
                           follow_redirects=False)
        assert response.headers
        assert 'Location' in response.headers
        loc = urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()

        assert loc == '/en/dataset/%s/resource/%s' % (pkg_id, ati_chromo['published_resource_id'])

        response = app.get('/en/resource/ati-nil',
                           extra_environ=self.extra_environ_tester,
                           environ_overrides=self.environ_overrides_tester,
                           status=302,
                           follow_redirects=False)
        assert response.headers
        assert 'Location' in response.headers
        loc = urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()

        assert loc == '/en/dataset/%s/resource/%s' % (pkg_id, ati_nil_chromo['published_resource_id'])
