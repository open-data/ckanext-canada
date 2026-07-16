# -*- coding: UTF-8 -*-
from ckanext.canada.tests import (
    CanadaTestBase,
    mock_is_registry_domain,
    mock_is_portal_domain,
    get_test_domains
)
import builtins  # noqa: F401
import re
import io
import pytest
import mock
import logging
import xml.etree.ElementTree as ET
from ckan.plugins.toolkit import h, config
from ckan.lib.jobs import get_queue
from ckan import plugins

from ckan.tests.helpers import CKANResponse  # noqa: F401
from ckan.model.types import make_uuid
from ckanapi import LocalCKAN
from ckan import model

from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaSysadminWithToken as Sysadmin
)
# type_ignore_reason: custom fixtures
from ckanext.canada.tests.fixtures import (  # noqa: F401
    mock_uploads,  # type: ignore
    use_xloader,  # type: ignore
)
from ckanext.canada.tests.helpers import (
    get_relative_offset_from_response,
    MockFieldStorage,
    get_sample_filepath,
)

logger = logging.getLogger(__name__)


class TestDomainMap(CanadaTestBase):
    """
    Tests for expected behaviour with the language_domains plugin.

    IMPORTANT: the Portal nginx for /data/ does rewrite /data/(.*) /$1
               which we cannot mock a reverse proxy here. Just do not
               include the /data/ in the offset for the requests.

    IMORTANT: if setting the CKAN_LANG in the test environ, the i18nMiddleware
              will NOT properly modify the PATH_INFO, resulting in 404s.
    """
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestDomainMap, self).setup_class()

        self.test_domain_map = get_test_domains()
        sysadmin = Sysadmin()
        self.sysadmin_action = LocalCKAN(username=sysadmin['name']).action
        self.extra_environ_tester_registry = {'Authorization': sysadmin['token'],
                                              'HTTP_HOST': self.test_domain_map['registry']['en']}
        self.extra_environ_tester_portal_en = {'Authorization': sysadmin['token'],
                                               'HTTP_HOST': self.test_domain_map['portal']['en']}
        self.extra_environ_tester_portal_fr = {'Authorization': sysadmin['token'],
                                               'HTTP_HOST': self.test_domain_map['portal']['fr']}
        self.environ_overrides_tester = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        self.org = Organization(users=[{
            'name': sysadmin['name'],
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
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=301,
                           follow_redirects=False)  # catch redirect

        offset, host = get_relative_offset_from_response(response)
        assert offset == '/data/fr/organization'
        assert host == self.test_domain_map['portal']['fr']

        # french domain to english domain
        offset = '/en/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
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
        # english request
        offset = '/en/dataset/'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        # test for both in the case that the i18n catalogues are built
        assert 'Search Records' in response.body or 'Search Datasets' in response.body
        assert '/fr/dataset/' in response.body

        # french request
        offset = '/fr/dataset/'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        # test for both in the case that the i18n catalogues are built
        assert 'Search Records' in response.body or 'Search Datasets' in response.body or 'Recherche de dossiers' in response.body
        assert '/en/dataset/' in response.body

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_no_redirect(self, app):
        """
        Requesting the correct language and domain should not do a redirect
        """
        # english request
        offset = '/en/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        assert 'Organizations' in response.body
        assert self.test_domain_map['portal']['fr'] + '/data/fr/organization' in response.body

        # french request
        offset = '/fr/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        # test for both in the case that the i18n catalogues are built
        assert 'Organizations' in response.body or 'Organisations' in response.body
        assert self.test_domain_map['portal']['en'] + '/data/en/organization' in response.body

    def _filled_dataset_form(self, dataset_id):
        return {
            'id': dataset_id,
            'owner_org': self.org['id'],
            'collection': 'primary',
            'title_translated-en': 'english title',
            'title_translated-fr': 'french title',
            'notes_translated-en': 'english description',
            'notes_translated-fr': 'french description',
            'subject': 'arts_music_literature',
            'keywords-en': 'english keywords',
            'keywords-fr': 'french keywords',
            'date_published': '2000-01-01',
            'ready_to_publish': 'true',
            'frequency': 'as_needed',
            'jurisdiction': 'federal',
            'license_id': 'ca-ogl-lgo',
            'restrictions': 'unrestricted',
            'imso_approval': 'true',
            'state': 'active',
            'portal_release_date': '2000-01-01',
            'save': '',
            '_ckan_phase': '1',
        }

    def _filled_dataset_dict(self, dataset_id):
        return {
            'id': dataset_id,
            'type': 'dataset',
            'owner_org': self.org['name'],
            'collection': 'primary',
            'title_translated': {'en': 'english title',
                                 'fr': 'french title'},
            'frequency': 'as_needed',
            'notes_translated': {'en': 'english description',
                                 'fr': 'french description'},
            'subject': ['arts_music_literature'],
            'date_published': '2000-01-01',
            'keywords': {'en': ['english keywords'],
                         'fr': ['french keywords']},
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
            'jurisdiction': 'federal',
            'restrictions': 'unrestricted',
            'resources': [],
            'portal_release_date': '2000-01-01',
            'state': 'active',
        }

    def _filled_resource_form(self, dataset_id):
        return {
            'id': '',
            'package_id': dataset_id,
            'name_translated-en': 'english resource name',
            'name_translated-fr': 'french resource name',
            'resource_type': 'dataset',
            'url': 'somewhere',
            'format': 'CSV',
            'language': 'en',
            # go-metadata = "Publish"
            # go-dataset-complete = "Add"
            'save': 'go-metadata',
        }

    def _filled_resource_dict(self, dataset_id):
        return {
            'package_id': dataset_id,
            'name_translated': {'en': 'english resource name',
                                'fr': 'french resource name'},
            'format': 'CSV',
            'url': 'somewhere',
            'resource_type': 'dataset',
            'language': ['en'],
        }

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    @pytest.mark.usefixtures('mock_uploads')
    def test_registry_resource_url(self, app, mock_uploads):  # noqa: F811
        """
        Creating uploaded resources should only store relative URIs
        in the database and in SOLR. package_show should prepend the
        requesting hostname to the resource URIs.
        """
        pkg_id = make_uuid()

        offset = h.url_for('dataset.new', locale='en')
        response = app.post(offset,
                            data=self._filled_dataset_form(pkg_id),
                            extra_environ=self.extra_environ_tester_registry,
                            environ_overrides=self.environ_overrides_tester,
                            status=302,
                            follow_redirects=False)  # catch redirect

        offset, _host = get_relative_offset_from_response(response)
        assert offset == f'/en/dataset/{pkg_id}/resource/new'

        res_form_fields = self._filled_resource_form(pkg_id)
        sample_filepath = get_sample_filepath('example_image_1.png')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_r1 = f.read()
            fake_file_obj.write(file_data_r1)
            mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'example_image_1.png')

        res_form_fields['url'] = 'example_image_1.png'
        res_form_fields['url_type'] = 'upload'
        res_form_fields['format'] = 'PNG'
        res_form_fields['upload'] = mock_field_store_r1

        response = app.post(offset,
                            data=res_form_fields,
                            extra_environ=self.extra_environ_tester_registry,
                            environ_overrides=self.environ_overrides_tester,
                            follow_redirects=False)  # catch redirect

        offset, _host = get_relative_offset_from_response(response)
        assert offset == f'/en/dataset/{pkg_id}'

        # check package_show in english
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/en/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['registry']['en'], pkg_id, res_dict['id'])

        # check database object
        res_obj = model.Resource.get(res_dict['id'])
        assert res_obj.url_type == 'upload'
        assert res_obj.url == 'example_image_1.png'

        # check resource_show in english
        offset = h.url_for('api.action', ver=3, logic_function='resource_show', id=res_dict['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        res_dict = response.json['result']

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/en/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['registry']['en'], pkg_id, res_dict['id'])

        # check package_show in french
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['registry']['fr'], pkg_id, res_dict['id'])

        # check resource_show in french
        offset = h.url_for('api.action', ver=3, logic_function='resource_show', id=res_dict['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        res_dict = response.json['result']

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['registry']['fr'], pkg_id, res_dict['id'])

        # check package_search
        offset = h.url_for('api.action', ver=3, logic_function='package_search',
                           include_private=1, fq=f'id:{pkg_id}', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json['result']['results']

        assert len(results) == 1
        assert results[0]['id'] == pkg_id
        assert len(results[0]['resources']) == 1
        # SOLR only stores relative, no root, no locale dir
        assert results[0]['resources'][0]['url'] == '/dataset/%s/resource/%s/download/example_image_1.png' % (
            pkg_id, res_dict['id'])

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    @pytest.mark.usefixtures('mock_uploads')
    def test_portal_resource_url(self, app, mock_uploads):  # noqa: F811
        """
        Creating uploaded resources should only store relative URIs
        in the database and in SOLR. package_show should prepend the
        requesting hostname to the resource URIs.

        NOTE: the Portal does not have webforms, using LocalCKAN.
        """
        pkg_id = make_uuid()

        pkg_dict = self.sysadmin_action.package_create(
            **self._filled_dataset_dict(pkg_id))

        res_post_dict = self._filled_resource_dict(pkg_id)
        sample_filepath = get_sample_filepath('example_image_1.png')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_r1 = f.read()
            fake_file_obj.write(file_data_r1)
            mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'example_image_1.png')

            fake_stream_r1 = io.BufferedReader(io.BytesIO(file_data_r1))

        with mock.patch('io.open', return_value=fake_stream_r1):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            res_post_dict['url'] = 'example_image_1.png'
            res_post_dict['url_type'] = 'upload'
            res_post_dict['format'] = 'PNG'
            res_post_dict['upload'] = mock_field_store_r1

            res_dict = self.sysadmin_action.resource_create(**res_post_dict)

        # check package_show in english
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/data/en/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])

        # check database object
        res_obj = model.Resource.get(res_dict['id'])
        assert res_obj.url_type == 'upload'
        assert res_obj.url == 'example_image_1.png'

        # check resource_show in english
        offset = h.url_for('api.action', ver=3, logic_function='resource_show', id=res_dict['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        res_dict = response.json['result']

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/data/en/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])

        # check package_show in french
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/data/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])

        # check resource_show in french
        offset = h.url_for('api.action', ver=3, logic_function='resource_show', id=res_dict['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        res_dict = response.json['result']

        assert res_dict['url_type'] == 'upload'
        assert res_dict['format'] == 'PNG'
        assert res_dict['url'] == 'http://%s/data/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])

        # check package_search
        offset = h.url_for('api.action', ver=3, logic_function='package_search',
                           include_private=1, fq=f'id:{pkg_id}', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json['result']['results']

        assert len(results) == 1
        assert results[0]['id'] == pkg_id
        assert len(results[0]['resources']) == 1
        # SOLR only stores relative, no root, no locale dir
        assert results[0]['resources'][0]['url'] == '/dataset/%s/resource/%s/download/example_image_1.png' % (
            pkg_id, res_dict['id'])

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_registry_api_help(self, app):
        """
        Help link in the API return should have the
        correct domain, root, and locale.
        """
        # english request
        offset = h.url_for('api.action', ver=3, logic_function='status_show', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json

        assert 'help' in results
        assert results['help'] == 'http://%s/en/api/3/action/help_show?name=status_show' % self.test_domain_map['registry']['en']

        # french request
        offset = h.url_for('api.action', ver=3, logic_function='status_show', locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json

        assert 'help' in results
        assert results['help'] == 'http://%s/fr/api/3/action/help_show?name=status_show' % self.test_domain_map['registry']['fr']

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_api_help(self, app):
        """
        Help link in the API return should have the
        correct domain, root, and locale.
        """
        # english request
        offset = h.url_for('api.action', ver=3, logic_function='status_show', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json

        assert 'help' in results
        assert results['help'] == 'http://%s/data/en/api/3/action/help_show?name=status_show' % self.test_domain_map['portal']['en']

        # french request
        offset = h.url_for('api.action', ver=3, logic_function='status_show', locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        results = response.json

        assert 'help' in results
        assert results['help'] == 'http://%s/data/fr/api/3/action/help_show?name=status_show' % self.test_domain_map['portal']['fr']

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    def test_registry_assets(self, app):
        """
        Webassets such as css, js, and images should have
        the correct domain, root, and locale.
        """
        # english request
        offset = '/en/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        assert 'Organizations' in response.body
        assert '/en/base/css/main.css' in response.body or re.search(r'/en/webassets/base/.{8}_main.css', response.body)
        assert '/en/base/vendor/jquery.js' in response.body or re.search(r'/en/webassets/vendor/.{8}_jquery.js', response.body)

        # french request
        offset = '/fr/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           follow_redirects=True)

        # test for both in the case that the i18n catalogues are built
        assert 'Organizations' in response.body or 'Organisations' in response.body
        assert '/fr/base/css/main.css' in response.body or re.search(r'/fr/webassets/base/.{8}_main.css', response.body)
        assert '/fr/base/vendor/jquery.js' in response.body or re.search(r'/fr/webassets/vendor/.{8}_jquery.js', response.body)

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_assets(self, app):
        """
        Webassets such as css, js, and images should have
        the correct domain, root, and locale.
        """
        # english request
        offset = '/en/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        assert 'Organizations' in response.body
        assert '/data/en/base/css/main.css' in response.body or re.search(r'/data/en/webassets/base/.{8}_main.css', response.body)
        assert '/data/en/base/vendor/jquery.js' in response.body or re.search(r'/data/en/webassets/vendor/.{8}_jquery.js', response.body)

        # french request
        offset = '/fr/organization'
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           follow_redirects=True)

        # test for both in the case that the i18n catalogues are built
        assert 'Organizations' in response.body or 'Organisations' in response.body
        assert '/data/fr/base/css/main.css' in response.body or re.search(r'/data/fr/webassets/base/.{8}_main.css', response.body)
        assert '/data/fr/base/vendor/jquery.js' in response.body or re.search(r'/data/fr/webassets/vendor/.{8}_jquery.js', response.body)

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    def test_portal_atom_feed_ids(self, app):
        """
        Generated ATOM feed IDs should have the
        the correct domain, root, and locale.

        NOTE: the Portal does not have webforms, using LocalCKAN.
        """
        pkg_id = make_uuid()

        res_post_dict = self._filled_resource_dict(pkg_id)
        pkg_post_dict = self._filled_dataset_dict(pkg_id)
        pkg_post_dict['resources'] = [res_post_dict]
        pkg_dict = self.sysadmin_action.package_create(
            **pkg_post_dict)

        atom_ns = {'atom': 'http://www.w3.org/2005/Atom'}
        feed_date = config.get('ckan.feeds.date')
        feed_author = config.get('ckan.feeds.author_name')

        # english request
        offset = h.url_for('feeds.dataset', id=pkg_id, locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        root = ET.fromstring(response.body)

        feed_id = root.find('atom:id', atom_ns).text
        feed_title = root.find('atom:title', atom_ns).text
        feed_sub_title = root.find('atom:subtitle', atom_ns).text
        links = root.findall('atom:link', atom_ns)

        assert feed_id == 'tag:http://%s,%s:/data/en/feeds/dataset/%s.atom' % (
            self.test_domain_map['portal']['en'], feed_date, pkg_id)
        assert pkg_dict['title_translated']['en'] in feed_title
        assert pkg_dict['title_translated']['en'] in feed_sub_title
        for link in links:
            if link.get('rel') == 'self':
                assert link.get('href') == 'http://%s/data/en/feeds/dataset/%s.atom' % (
                    self.test_domain_map['portal']['en'], pkg_id)
            if link.get('rel') == 'enclosure':
                assert link.get('href') == 'http://%s/data/en/api/3/action/package_show?id=%s' % (
                    self.test_domain_map['portal']['en'], pkg_id)
            if link.get('rel') == 'alternate':
                assert link.get('href') == 'http://%s/data/en/dataset/%s' % (
                    self.test_domain_map['portal']['en'], pkg_id)

        author_name = root.find('atom:author', atom_ns).find('atom:name', atom_ns).text
        assert author_name == feed_author

        entries = root.findall('atom:entry', atom_ns)
        entry_id = entries[0].find('atom:id', atom_ns).text
        entry_title = entries[0].find('atom:title', atom_ns).text
        entry_links = entries[0].findall('atom:link', atom_ns)

        assert len(entries) == 1
        assert entry_id == 'tag:http://%s,%s:/data/en/dataset/%s/resource/%s' % (
            self.test_domain_map['portal']['en'], feed_date, pkg_id, pkg_dict['resources'][0]['id'])
        assert entry_title == pkg_dict['resources'][0]['name_translated']['en']
        for link in entry_links:
            if link.get('rel') == 'enclosure':
                assert link.get('href') == 'http://%s/data/en/api/3/action/resource_show?id=%s' % (
                    self.test_domain_map['portal']['en'], pkg_dict['resources'][0]['id'])
            if link.get('rel') == 'alternate':
                assert link.get('href') == 'http://%s/data/en/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['en'], pkg_id, pkg_dict['resources'][0]['id'])

        # french request
        offset = h.url_for('feeds.dataset', id=pkg_id, locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        root = ET.fromstring(response.body)

        feed_id = root.find('atom:id', atom_ns).text
        feed_title = root.find('atom:title', atom_ns).text
        feed_sub_title = root.find('atom:subtitle', atom_ns).text
        links = root.findall('atom:link', atom_ns)

        assert feed_id == 'tag:http://%s,%s:/data/fr/feeds/dataset/%s.atom' % (
            self.test_domain_map['portal']['fr'], feed_date, pkg_id)
        assert pkg_dict['title_translated']['fr'] in feed_title
        assert pkg_dict['title_translated']['fr'] in feed_sub_title
        for link in links:
            if link.get('rel') == 'self':
                assert link.get('href') == 'http://%s/data/fr/feeds/dataset/%s.atom' % (
                    self.test_domain_map['portal']['fr'], pkg_id)
            if link.get('rel') == 'enclosure':
                assert link.get('href') == 'http://%s/data/fr/api/3/action/package_show?id=%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id)
            if link.get('rel') == 'alternate':
                assert link.get('href') == 'http://%s/data/fr/dataset/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id)

        author_name = root.find('atom:author', atom_ns).find('atom:name', atom_ns).text
        assert author_name == feed_author

        entries = root.findall('atom:entry', atom_ns)
        entry_id = entries[0].find('atom:id', atom_ns).text
        entry_title = entries[0].find('atom:title', atom_ns).text
        entry_links = entries[0].findall('atom:link', atom_ns)

        assert len(entries) == 1
        assert entry_id == 'tag:http://%s,%s:/data/fr/dataset/%s/resource/%s' % (
            self.test_domain_map['portal']['fr'], feed_date, pkg_id, pkg_dict['resources'][0]['id'])
        assert entry_title == pkg_dict['resources'][0]['name_translated']['fr']
        for link in entry_links:
            if link.get('rel') == 'enclosure':
                assert link.get('href') == 'http://%s/data/fr/api/3/action/resource_show?id=%s' % (
                    self.test_domain_map['portal']['fr'], pkg_dict['resources'][0]['id'])
            if link.get('rel') == 'alternate':
                assert link.get('href') == 'http://%s/data/fr/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id, pkg_dict['resources'][0]['id'])

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    @pytest.mark.usefixtures('mock_uploads')
    def test_portal_dcat_fields(self, app, mock_uploads):  # noqa: F811
        """
        Generated DCAT IDs should have the
        the correct domain, root, and locale.

        NOTE: the Portal does not have webforms, using LocalCKAN.
        """
        pkg_id = make_uuid()

        pkg_dict = self.sysadmin_action.package_create(
            **self._filled_dataset_dict(pkg_id))

        res_post_dict = self._filled_resource_dict(pkg_id)
        sample_filepath = get_sample_filepath('example_image_1.png')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_r1 = f.read()
            fake_file_obj.write(file_data_r1)
            mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'example_image_1.png')

            fake_stream_r1 = io.BufferedReader(io.BytesIO(file_data_r1))

        with mock.patch('io.open', return_value=fake_stream_r1):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            res_post_dict['url'] = 'example_image_1.png'
            res_post_dict['url_type'] = 'upload'
            res_post_dict['format'] = 'PNG'
            res_post_dict['upload'] = mock_field_store_r1

            res_dict = self.sysadmin_action.resource_create(**res_post_dict)

        # test dcat JSON-LD

        # english request
        offset = '/en/dataset/%s.jsonld' % pkg_id
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        graph_data = response.json['@graph']
        for obj in graph_data:
            # test org map
            if obj['@type'] == 'foaf:Organization':
                assert obj['@id'] == 'http://%s/data/en/organization/%s' % (
                    self.test_domain_map['portal']['en'], pkg_dict['owner_org'])
                for entry in obj['foaf:name']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == self.org['title_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == self.org['title_translated']['fr']
            # test resource map
            if obj['@type'] == 'dcat:Distribution':
                assert obj['@id'] == 'http://%s/data/en/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])
                assert obj['dcat:accessURL']['@id'] == 'http://%s/data/en/dataset/%s/resource/%s/download/example_image_1.png' % (
                    self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])
                assert obj['dct:format'] == res_dict['format']
                for entry in obj['dct:title']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == res_dict['name_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == res_dict['name_translated']['fr']
            # test dataset map
            if obj['@type'] == 'dcat:Dataset':
                assert obj['@id'] == 'http://%s/data/en/dataset/%s' % (
                    self.test_domain_map['portal']['en'], pkg_id)
                assert obj['dcat:distribution']['@id'] == 'http://%s/data/en/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])
                for entry in obj['dcat:keyword']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['keywords']['en'][0]
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['keywords']['fr'][0]
                assert obj['dct:accrualPeriodicity'] == pkg_dict['frequency']
                assert obj['dct:identifier'] == pkg_dict['id']
                for entry in obj['dct:description']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['notes_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['notes_translated']['fr']
                assert obj['dct:publisher']['@id'] == 'http://%s/data/en/organization/%s' % (
                    self.test_domain_map['portal']['en'], pkg_dict['owner_org'])
                for entry in obj['dct:title']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['title_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['title_translated']['fr']

        # french request
        offset = '/fr/dataset/%s.jsonld' % pkg_id
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        graph_data = response.json['@graph']
        for obj in graph_data:
            # test org map
            if obj['@type'] == 'foaf:Organization':
                assert obj['@id'] == 'http://%s/data/fr/organization/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_dict['owner_org'])
                for entry in obj['foaf:name']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == self.org['title_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == self.org['title_translated']['fr']
            # test resource map
            if obj['@type'] == 'dcat:Distribution':
                assert obj['@id'] == 'http://%s/data/fr/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])
                assert obj['dcat:accessURL']['@id'] == 'http://%s/data/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
                    self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])
                assert obj['dct:format'] == res_dict['format']
                for entry in obj['dct:title']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == res_dict['name_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == res_dict['name_translated']['fr']
            # test dataset map
            if obj['@type'] == 'dcat:Dataset':
                assert obj['@id'] == 'http://%s/data/fr/dataset/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id)
                assert obj['dcat:distribution']['@id'] == 'http://%s/data/fr/dataset/%s/resource/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])
                for entry in obj['dcat:keyword']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['keywords']['en'][0]
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['keywords']['fr'][0]
                assert obj['dct:accrualPeriodicity'] == pkg_dict['frequency']
                assert obj['dct:identifier'] == pkg_dict['id']
                for entry in obj['dct:description']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['notes_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['notes_translated']['fr']
                assert obj['dct:publisher']['@id'] == 'http://%s/data/fr/organization/%s' % (
                    self.test_domain_map['portal']['fr'], pkg_dict['owner_org'])
                for entry in obj['dct:title']:
                    if entry['@language'] == 'en':
                        assert entry['@value'] == pkg_dict['title_translated']['en']
                    if entry['@language'] == 'fr':
                        assert entry['@value'] == pkg_dict['title_translated']['fr']

        # test dcat XML
        rdf_ns = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        dcat_ns = {
            'rdf': rdf_ns,
            'dct': 'http://purl.org/dc/terms/',
            'dcat': 'http://www.w3.org/ns/dcat#',
            'foaf': 'http://xmlns.com/foaf/0.1/',
        }

        # english request
        offset = '/en/dataset/%s.xml' % pkg_id
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        root = ET.fromstring(response.body)
        dataset = root.find('dcat:Dataset', dcat_ns)
        publisher = dataset.find('dct:publisher', dcat_ns).find('foaf:Organization', dcat_ns)
        distributions = dataset.findall('dcat:distribution', dcat_ns)

        # test org map
        org_names = publisher.findall('foaf:name', dcat_ns)
        for name in org_names:
            if name.get('xml:lang') == 'en':
                assert name.text == self.org['title_translated']['en']
            if name.get('xml:lang') == 'fr':
                assert name.text == self.org['title_translated']['fr']
        assert publisher.get(f'{{{rdf_ns}}}about') == 'http://%s/data/en/organization/%s' % (
            self.test_domain_map['portal']['en'], pkg_dict['owner_org'])
        # test resource map
        assert len(distributions) == 1
        resource = distributions[0].find('dcat:Distribution', dcat_ns)
        resource_titles = resource.findall('dct:title', dcat_ns)
        for title in resource_titles:
            if title.get('xml:lang') == 'en':
                assert title.text == res_dict['name_translated']['en']
            if title.get('xml:lang') == 'fr':
                assert title.text == res_dict['name_translated']['fr']
        assert resource.get(f'{{{rdf_ns}}}about') == 'http://%s/data/en/dataset/%s/resource/%s' % (
            self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])
        assert resource.find('dct:format', dcat_ns).text == res_dict['format']
        assert resource.find('dcat:accessURL', dcat_ns).get(f'{{{rdf_ns}}}resource') == 'http://%s/data/en/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['en'], pkg_id, res_dict['id'])
        # test dataset map
        dataset_titles = dataset.findall('dct:title', dcat_ns)
        dataset_descriptions = dataset.findall('dct:description', dcat_ns)
        dataset_keywords = dataset.findall('dcat:keyword', dcat_ns)
        for title in dataset_titles:
            if title.get('xml:lang') == 'en':
                assert title.text == pkg_dict['title_translated']['en']
            if title.get('xml:lang') == 'fr':
                assert title.text == pkg_dict['title_translated']['fr']
        for description in dataset_descriptions:
            if description.get('xml:lang') == 'en':
                assert description.text == pkg_dict['notes_translated']['en']
            if description.get('xml:lang') == 'fr':
                assert description.text == pkg_dict['notes_translated']['fr']
        for keyword in dataset_keywords:
            if keyword.get('xml:lang') == 'en':
                assert keyword.text == pkg_dict['keywords']['en'][0]
            if keyword.get('xml:lang') == 'fr':
                assert keyword.text == pkg_dict['keywords']['fr'][0]
        assert dataset.find('dct:identifier', dcat_ns).text == pkg_dict['id']
        assert dataset.find('dct:accrualPeriodicity', dcat_ns).text == pkg_dict['frequency']

        # french request
        offset = '/fr/dataset/%s.xml' % pkg_id
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        root = ET.fromstring(response.body)
        dataset = root.find('dcat:Dataset', dcat_ns)
        publisher = dataset.find('dct:publisher', dcat_ns).find('foaf:Organization', dcat_ns)
        distributions = dataset.findall('dcat:distribution', dcat_ns)

        # test org map
        org_names = publisher.findall('foaf:name', dcat_ns)
        for name in org_names:
            if name.get('xml:lang') == 'en':
                assert name.text == self.org['title_translated']['en']
            if name.get('xml:lang') == 'fr':
                assert name.text == self.org['title_translated']['fr']
        assert publisher.get(f'{{{rdf_ns}}}about') == 'http://%s/data/fr/organization/%s' % (
            self.test_domain_map['portal']['fr'], pkg_dict['owner_org'])
        # test resource map
        assert len(distributions) == 1
        resource = distributions[0].find('dcat:Distribution', dcat_ns)
        resource_titles = resource.findall('dct:title', dcat_ns)
        for title in resource_titles:
            if title.get('xml:lang') == 'en':
                assert title.text == res_dict['name_translated']['en']
            if title.get('xml:lang') == 'fr':
                assert title.text == res_dict['name_translated']['fr']
        assert resource.get(f'{{{rdf_ns}}}about') == 'http://%s/data/fr/dataset/%s/resource/%s' % (
            self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])
        assert resource.find('dct:format', dcat_ns).text == res_dict['format']
        assert resource.find('dcat:accessURL', dcat_ns).get(f'{{{rdf_ns}}}resource') == 'http://%s/data/fr/dataset/%s/resource/%s/download/example_image_1.png' % (
            self.test_domain_map['portal']['fr'], pkg_id, res_dict['id'])
        # test dataset map
        dataset_titles = dataset.findall('dct:title', dcat_ns)
        dataset_descriptions = dataset.findall('dct:description', dcat_ns)
        dataset_keywords = dataset.findall('dcat:keyword', dcat_ns)
        for title in dataset_titles:
            if title.get('xml:lang') == 'en':
                assert title.text == pkg_dict['title_translated']['en']
            if title.get('xml:lang') == 'fr':
                assert title.text == pkg_dict['title_translated']['fr']
        for description in dataset_descriptions:
            if description.get('xml:lang') == 'en':
                assert description.text == pkg_dict['notes_translated']['en']
            if description.get('xml:lang') == 'fr':
                assert description.text == pkg_dict['notes_translated']['fr']
        for keyword in dataset_keywords:
            if keyword.get('xml:lang') == 'en':
                assert keyword.text == pkg_dict['keywords']['en'][0]
            if keyword.get('xml:lang') == 'fr':
                assert keyword.text == pkg_dict['keywords']['fr'][0]
        assert dataset.find('dct:identifier', dcat_ns).text == pkg_dict['id']
        assert dataset.find('dct:accrualPeriodicity', dcat_ns).text == pkg_dict['frequency']

    @mock.patch.object(h, 'is_registry_domain', mock_is_registry_domain)
    @pytest.mark.usefixtures('use_xloader')
    @pytest.mark.usefixtures('mock_uploads')
    def test_registry_datastore_urls(self, app, mock_uploads):  # noqa: F811
        """
        Creating XLoader resources should only store relative URIs
        in the database and in SOLR. datastore_search should prepend the
        requesting hostname to the paging URIs.
        """
        queue = get_queue('test_queue')
        queue.empty()
        pkg_id = make_uuid()

        offset = h.url_for('dataset.new', locale='en')
        response = app.post(offset,
                            data=self._filled_dataset_form(pkg_id),
                            extra_environ=self.extra_environ_tester_registry,
                            environ_overrides=self.environ_overrides_tester,
                            status=302,
                            follow_redirects=False)  # catch redirect

        offset, _host = get_relative_offset_from_response(response)
        assert offset == f'/en/dataset/{pkg_id}/resource/new'

        res_form_fields = self._filled_resource_form(pkg_id)
        sample_filepath = get_sample_filepath('sample.csv')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_r1 = f.read()
            fake_file_obj.write(file_data_r1)
            mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'sample.csv')

        res_form_fields['url'] = 'sample.csv'
        res_form_fields['url_type'] = 'upload'
        res_form_fields['format'] = 'CSV'
        res_form_fields['upload'] = mock_field_store_r1

        response = app.post(offset,
                            data=res_form_fields,
                            extra_environ=self.extra_environ_tester_registry,
                            environ_overrides=self.environ_overrides_tester,
                            follow_redirects=False)  # catch redirect

        # load file into the datastore
        pkg_dict = self.sysadmin_action.package_show(id=pkg_id)

        def _fake_open(*args, **kwargs):
            return io.BufferedReader(io.BytesIO(file_data_r1))

        # should have a ckanext-validation job queued right now
        jobs = queue.jobs
        assert len(jobs) == 1
        job = jobs[0]
        assert job.func_name == 'ckanext.validation.jobs.run_validation_job'
        assert job.meta['title'] == 'Validate Resource'
        with mock.patch('io.open', _fake_open), mock.patch('builtins.open', _fake_open):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            job.func(*job.args, **job.kwargs)
        queue.remove(job)
        job.delete()

        # check resource_validation_show in english
        offset = h.url_for('api.action', ver=3, logic_function='resource_validation_show',
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        validation_report = response.json['result']

        assert validation_report['error'] is None
        assert validation_report['language'] == 'en'
        assert validation_report['resource_id'] == pkg_dict['resources'][0]['id']
        assert validation_report['status'] == 'success'

        # check resource_validation_show in french
        offset = h.url_for('api.action', ver=3, logic_function='resource_validation_show',
                           resource_id=pkg_dict['resources'][0]['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        validation_report = response.json['result']

        assert validation_report['error'] is None
        assert validation_report['language'] == 'fr'
        assert validation_report['resource_id'] == pkg_dict['resources'][0]['id']
        assert validation_report['status'] == 'success'

        # submit it to XLoader as the xloader_submit action is what adds ckan_url and original_url
        offset = h.url_for('api.action', ver=3, logic_function='xloader_submit', ignore_hash=True,
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.post(offset,
                            data={
                                'resource_id': pkg_dict['resources'][0]['id'],
                                'ignore_hash': True
                            },
                            extra_environ=self.extra_environ_tester_registry,
                            environ_overrides=self.environ_overrides_tester,
                            status=400,
                            follow_redirects=False)  # no need for redirects
        print('   ')
        print('DEBUGGING:: STEP 1')
        print('   ')
        print('XLOADER LOADED:')
        print(plugins.plugin_loaded('xloader'))
        print('VALIDATION LOADED:')
        print(plugins.plugin_loaded('validation'))
        print('RESPONSE:')
        print(response)
        print('RESPONSE HEADERS:')
        print(response.headers)
        print('RESPONSE JSON:')
        print(response.json)
        print('   ')
        assert False
        response = response.json

        task = self.sysadmin_action.xloader_status(resource_id=pkg_dict['resources'][0]['id'])
        assert task['error'] == {}
        assert task['status'] == 'pending'
        assert response['help'] == 'http://%s/en/api/3/action/help_show?name=xloader_submit' % (
            self.test_domain_map['registry']['en'])
        assert response['success'] is True

        # should have a ckanext-xloader job queued right now
        jobs = queue.jobs
        assert len(jobs) == 1
        job = jobs[0]
        assert job.func_name == 'ckanext.xloader.jobs.xloader_data_into_datastore'
        assert job.meta['title'] == 'Upload to DataStore'
        assert job.args[0]['metadata']['ckan_url'] is None
        assert job.args[0]['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert job.args[0]['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])

        rq_job = mock.Mock()
        rq_job.meta = {}
        rq_job.id = task['job_id']

        file_response = mock.Mock()
        file_response.status_code = 200
        file_response.raw = io.BytesIO(file_data_r1)
        file_response.iter_content.return_value = [
            file_data_r1,
        ]
        file_response.headers = {}
        file_response.url = pkg_dict['resources'][0]['url']

        with mock.patch('ckanext.xloader.jobs.get_current_job', return_value=rq_job), \
             mock.patch('ckanext.xloader.jobs.requests.get', return_value=file_response):
            # NOTE: because XLoader is coded in a specific way which expects to be inside
            #       of the Redis Job worker process, we need to patch get_current_job.
            # NOTE: because XLoader uses requests.get we have to patch it, as it will always
            #       be outside of the app/test request context.
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            job.func(*job.args, **job.kwargs)
        queue.remove(job)
        job.delete()

        # check task_status_show in english
        offset = h.url_for('api.action', ver=3, logic_function='task_status_show',
                           entity_id=pkg_dict['resources'][0]['id'], task_type='xloader',
                           key='xloader', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        task_status = response.json['result']

        assert task_status['error'] == r'{}'
        assert task_status['state'] == 'complete'

        # check task_status_show in french
        offset = h.url_for('api.action', ver=3, logic_function='task_status_show',
                           entity_id=pkg_dict['resources'][0]['id'], task_type='xloader',
                           key='xloader', locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        task_status = response.json['result']

        assert task_status['error'] == r'{}'
        assert task_status['state'] == 'complete'

        # check xloader_status in english
        offset = h.url_for('api.action', ver=3, logic_function='xloader_status',
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        xloader_job = response.json['result']

        assert xloader_job['error'] == {}
        assert xloader_job['job_id'] == rq_job.id
        assert xloader_job['status'] == 'complete'
        assert xloader_job['task_info']['data']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['data']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['data']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['error'] is None
        assert xloader_job['task_info']['job_id'] == rq_job.id
        assert xloader_job['task_info']['status'] == 'complete'

        # check xloader_status in french
        offset = h.url_for('api.action', ver=3, logic_function='xloader_status',
                           resource_id=pkg_dict['resources'][0]['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        xloader_job = response.json['result']

        assert xloader_job['error'] == {}
        assert xloader_job['job_id'] == rq_job.id
        assert xloader_job['status'] == 'complete'
        assert xloader_job['task_info']['data']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['data']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['data']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['error'] is None
        assert xloader_job['task_info']['job_id'] == rq_job.id
        assert xloader_job['task_info']['status'] == 'complete'

        # check package_show in english
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url'] == 'http://%s/en/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['registry']['en'], pkg_id, pkg_dict['resources'][0]['id'])
        assert res_dict['original_url'] == 'http://%s/en/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['registry']['en'], pkg_id, pkg_dict['resources'][0]['id'])

        # check package_show in french
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url'] == 'http://%s/fr/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['registry']['fr'], pkg_id, pkg_dict['resources'][0]['id'])
        assert res_dict['original_url'] == 'http://%s/fr/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['registry']['fr'], pkg_id, pkg_dict['resources'][0]['id'])

        # check datastore_search in english
        offset = h.url_for('api.action', ver=3, logic_function='datastore_search',
                           resource_id=res_dict['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        response = response.json

        assert response['help'] == 'http://%s/en/api/3/action/help_show?name=datastore_search' % (
            self.test_domain_map['registry']['en'])
        assert response['result']['_links']['start'] == 'http://%s/en/api/3/action/datastore_search?resource_id=%s' % (
            self.test_domain_map['registry']['en'], res_dict['id'])
        assert response['result']['_links']['next'] == 'http://%s/en/api/3/action/datastore_search?resource_id=%s&offset=100' % (
            self.test_domain_map['registry']['en'], res_dict['id'])

        # check datastore_search in french
        offset = h.url_for('api.action', ver=3, logic_function='datastore_search',
                           resource_id=res_dict['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        response = response.json

        assert response['help'] == 'http://%s/fr/api/3/action/help_show?name=datastore_search' % (
            self.test_domain_map['registry']['fr'])
        assert response['result']['_links']['start'] == 'http://%s/fr/api/3/action/datastore_search?resource_id=%s' % (
            self.test_domain_map['registry']['fr'], res_dict['id'])
        assert response['result']['_links']['next'] == 'http://%s/fr/api/3/action/datastore_search?resource_id=%s&offset=100' % (
            self.test_domain_map['registry']['fr'], res_dict['id'])

    @mock.patch.object(h, 'is_registry_domain', mock_is_portal_domain)
    @pytest.mark.usefixtures('use_xloader')
    @pytest.mark.usefixtures('mock_uploads')
    def test_portal_datastore_urls(self, app, mock_uploads):  # noqa: F811
        """
        Creating XLoader resources should only store relative URIs
        in the database and in SOLR. datastore_search should prepend the
        requesting hostname to the paging URIs.

        NOTE: the Portal does not have webforms, using LocalCKAN.
        """
        queue = get_queue('test_queue')
        queue.empty()
        pkg_id = make_uuid()

        pkg_dict = self.sysadmin_action.package_create(
            **self._filled_dataset_dict(pkg_id))

        res_post_dict = self._filled_resource_dict(pkg_id)
        sample_filepath = get_sample_filepath('sample.csv')
        fake_file_obj = io.BytesIO()
        with open(sample_filepath, 'rb') as f:
            file_data_r1 = f.read()
            fake_file_obj.write(file_data_r1)
            mock_field_store_r1 = MockFieldStorage(fake_file_obj, 'sample.csv')

            fake_stream_r1 = io.BufferedReader(io.BytesIO(file_data_r1))

        with mock.patch('io.open', return_value=fake_stream_r1):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            res_post_dict['url'] = 'sample.csv'
            res_post_dict['url_type'] = 'upload'
            res_post_dict['format'] = 'CSV'
            res_post_dict['upload'] = mock_field_store_r1

            res_dict = self.sysadmin_action.resource_create(**res_post_dict)

        # load file into the datastore
        pkg_dict = self.sysadmin_action.package_show(id=pkg_id)

        def _fake_open(*args, **kwargs):
            return io.BufferedReader(io.BytesIO(file_data_r1))

        # should have a ckanext-validation job queued right now
        jobs = queue.jobs
        assert len(jobs) == 1
        job = jobs[0]
        assert job.func_name == 'ckanext.validation.jobs.run_validation_job'
        assert job.meta['title'] == 'Validate Resource'
        with mock.patch('io.open', _fake_open), mock.patch('builtins.open', _fake_open):
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            job.func(*job.args, **job.kwargs)
        queue.remove(job)
        job.delete()

        # check resource_validation_show in english
        offset = h.url_for('api.action', ver=3, logic_function='resource_validation_show',
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        validation_report = response.json['result']

        assert validation_report['error'] is None
        assert validation_report['language'] == 'en'
        assert validation_report['resource_id'] == pkg_dict['resources'][0]['id']
        assert validation_report['status'] == 'success'

        # check resource_validation_show in french
        offset = h.url_for('api.action', ver=3, logic_function='resource_validation_show',
                           resource_id=pkg_dict['resources'][0]['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        validation_report = response.json['result']

        assert validation_report['error'] is None
        assert validation_report['language'] == 'fr'
        assert validation_report['resource_id'] == pkg_dict['resources'][0]['id']
        assert validation_report['status'] == 'success'

        # submit it to XLoader as the xloader_submit action is what adds ckan_url and original_url
        offset = h.url_for('api.action', ver=3, logic_function='xloader_submit', ignore_hash=True,
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.post(offset,
                            data={
                                'resource_id': pkg_dict['resources'][0]['id'],
                                'ignore_hash': True
                            },
                            extra_environ=self.extra_environ_tester_portal_en,
                            environ_overrides=self.environ_overrides_tester,
                            status=400,
                            follow_redirects=False)  # no need for redirects
        print('   ')
        print('DEBUGGING:: STEP 1')
        print('   ')
        print('XLOADER LOADED:')
        print(plugins.plugin_loaded('xloader'))
        print('VALIDATION LOADED:')
        print(plugins.plugin_loaded('validation'))
        print('RESPONSE:')
        print(response)
        print('RESPONSE HEADERS:')
        print(response.headers)
        print('RESPONSE JSON:')
        print(response.json)
        print('   ')
        assert False
        response = response.json

        task = self.sysadmin_action.xloader_status(resource_id=pkg_dict['resources'][0]['id'])
        assert task['error'] == {}
        assert task['status'] == 'pending'
        assert response['help'] == 'http://%s/data/en/api/3/action/help_show?name=xloader_submit' % (
            self.test_domain_map['portal']['en'])
        assert response['success'] is True

        # should have a ckanext-xloader job queued right now
        jobs = queue.jobs
        assert len(jobs) == 1
        job = jobs[0]
        assert job.func_name == 'ckanext.xloader.jobs.xloader_data_into_datastore'
        assert job.meta['title'] == 'Upload to DataStore'
        assert job.args[0]['metadata']['ckan_url'] is None
        assert job.args[0]['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert job.args[0]['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])

        rq_job = mock.Mock()
        rq_job.meta = {}
        rq_job.id = task['job_id']

        file_response = mock.Mock()
        file_response.status_code = 200
        file_response.raw = io.BytesIO(file_data_r1)
        file_response.iter_content.return_value = [
            file_data_r1,
        ]
        file_response.headers = {}
        file_response.url = pkg_dict['resources'][0]['url']

        with mock.patch('ckanext.xloader.jobs.get_current_job', return_value=rq_job), \
             mock.patch('ckanext.xloader.jobs.requests.get', return_value=file_response):
            # NOTE: because XLoader is coded in a specific way which expects to be inside
            #       of the Redis Job worker process, we need to patch get_current_job.
            # NOTE: because XLoader uses requests.get we have to patch it, as it will always
            #       be outside of the app/test request context.
            model.Session.commit()
            model.Session.remove()
            _session = model.Session  # noqa: F841
            job.func(*job.args, **job.kwargs)
        queue.remove(job)
        job.delete()

        # check task_status_show in english
        offset = h.url_for('api.action', ver=3, logic_function='task_status_show',
                           entity_id=pkg_dict['resources'][0]['id'], task_type='xloader',
                           key='xloader', locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        task_status = response.json['result']

        assert task_status['error'] == r'{}'
        assert task_status['state'] == 'complete'

        # check task_status_show in french
        offset = h.url_for('api.action', ver=3, logic_function='task_status_show',
                           entity_id=pkg_dict['resources'][0]['id'], task_type='xloader',
                           key='xloader', locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        task_status = response.json['result']

        assert task_status['error'] == r'{}'
        assert task_status['state'] == 'complete'

        # check xloader_status in english
        offset = h.url_for('api.action', ver=3, logic_function='xloader_status',
                           resource_id=pkg_dict['resources'][0]['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        xloader_job = response.json['result']

        assert xloader_job['error'] == {}
        assert xloader_job['job_id'] == rq_job.id
        assert xloader_job['status'] == 'complete'
        assert xloader_job['task_info']['data']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['data']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['data']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['error'] is None
        assert xloader_job['task_info']['job_id'] == rq_job.id
        assert xloader_job['task_info']['status'] == 'complete'

        # check xloader_status in french
        offset = h.url_for('api.action', ver=3, logic_function='xloader_status',
                           resource_id=pkg_dict['resources'][0]['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        xloader_job = response.json['result']

        assert xloader_job['error'] == {}
        assert xloader_job['job_id'] == rq_job.id
        assert xloader_job['status'] == 'complete'
        assert xloader_job['task_info']['data']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['data']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['data']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['metadata']['ckan_url'] is None
        assert xloader_job['task_info']['metadata']['resource_id'] == pkg_dict['resources'][0]['id']
        assert xloader_job['task_info']['metadata']['original_url'] == '/dataset/%s/resource/%s/download/sample.csv' % (
            pkg_id, pkg_dict['resources'][0]['id'])
        assert xloader_job['task_info']['error'] is None
        assert xloader_job['task_info']['job_id'] == rq_job.id
        assert xloader_job['task_info']['status'] == 'complete'

        # check package_show in english
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url'] == 'http://%s/data/en/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['portal']['en'], pkg_id, pkg_dict['resources'][0]['id'])
        assert res_dict['original_url'] == 'http://%s/data/en/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['portal']['en'], pkg_id, pkg_dict['resources'][0]['id'])

        # check package_show in french
        offset = h.url_for('api.action', ver=3, logic_function='package_show', id=pkg_id, locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        pkg_dict = response.json['result']
        res_dict = pkg_dict['resources'][0]

        assert res_dict['url'] == 'http://%s/data/fr/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['portal']['fr'], pkg_id, pkg_dict['resources'][0]['id'])
        assert res_dict['original_url'] == 'http://%s/data/fr/dataset/%s/resource/%s/download/sample.csv' % (
            self.test_domain_map['portal']['fr'], pkg_id, pkg_dict['resources'][0]['id'])

        # check datastore_search in english
        offset = h.url_for('api.action', ver=3, logic_function='datastore_search',
                           resource_id=res_dict['id'], locale='en')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_en,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        response = response.json

        assert response['help'] == 'http://%s/data/en/api/3/action/help_show?name=datastore_search' % (
            self.test_domain_map['portal']['en'])
        assert response['result']['_links']['start'] == 'http://%s/data/en/api/3/action/datastore_search?resource_id=%s' % (
            self.test_domain_map['portal']['en'], res_dict['id'])
        assert response['result']['_links']['next'] == 'http://%s/data/en/api/3/action/datastore_search?resource_id=%s&offset=100' % (
            self.test_domain_map['portal']['en'], res_dict['id'])

        # check datastore_search in french
        offset = h.url_for('api.action', ver=3, logic_function='datastore_search',
                           resource_id=res_dict['id'], locale='fr')
        response = app.get(offset, extra_environ=self.extra_environ_tester_portal_fr,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects
        response = response.json

        assert response['help'] == 'http://%s/data/fr/api/3/action/help_show?name=datastore_search' % (
            self.test_domain_map['portal']['fr'])
        assert response['result']['_links']['start'] == 'http://%s/data/fr/api/3/action/datastore_search?resource_id=%s' % (
            self.test_domain_map['portal']['fr'], res_dict['id'])
        assert response['result']['_links']['next'] == 'http://%s/data/fr/api/3/action/datastore_search?resource_id=%s&offset=100' % (
            self.test_domain_map['portal']['fr'], res_dict['id'])
