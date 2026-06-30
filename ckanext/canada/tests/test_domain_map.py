# -*- coding: UTF-8 -*-
from ckanext.canada.tests import (
    CanadaTestBase,
    mock_is_registry_domain,
    mock_is_portal_domain,
    get_test_domains
)
import io
import pytest
import mock
from ckan.plugins.toolkit import h

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
)
from ckanext.canada.tests.helpers import (
    get_relative_offset_from_response,
    MockFieldStorage,
    get_sample_filepath,
)


@pytest.mark.usefixtures('with_request_context')
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

        assert 'Search Records' in response.body
        assert '/fr/dataset/' in response.body

        # french request
        offset = '/fr/dataset/'
        response = app.get(offset, extra_environ=self.extra_environ_tester_registry,
                           environ_overrides=self.environ_overrides_tester,
                           status=200,
                           follow_redirects=False)  # no need for redirects

        # test for both in the case that the i18n catalogues are not built
        assert 'Search Records' in response.body or 'Recherche de dossiers' in response.body
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

        # test for both in the case that the i18n catalogues are not built
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

    # TODO: atom/feeds ids
    # TODO: datastore search paging
    # TODO: dcat ids
