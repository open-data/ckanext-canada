# -*- coding: UTF-8 -*-
import mock
from ckanext.canada.tests import CanadaTestBase
import pytest
from urllib.parse import urlparse
from io import BytesIO
from openpyxl.workbook import Workbook
from ckan.plugins.toolkit import h
from ckanapi import (
    LocalCKAN,
    ValidationError
)

from ckan.tests.helpers import CKANResponse

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User,
)
from ckanext.canada.tests.fixtures import (
    mock_isfile,
    mock_open_ip_list,
    MOCK_IP_ADDRESS,
)

from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.read_excel import read_excel
from ckanext.recombinant.write_excel import (
    excel_template,
    fill_cell,
    DATA_FIRST_ROW,
    DATA_FIRST_COL_NUM
)


def _get_relative_offset_from_response(response):
    # type: (CKANResponse) -> str
    assert response.headers
    assert 'Location' in response.headers
    return urlparse(response.headers['Location'])._replace(scheme='', netloc='').geturl()


@pytest.mark.usefixtures('with_request_context')
class TestPackageWebForms(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestPackageWebForms, self).setup_method(method)
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.dataset_id = 'f3e4adb9-6e32-4cb4-bf68-1eab9d1288f4'
        self.resource_id = '8b29e2c6-8a12-4537-bf97-fe4e5f0a14c1'


    def test_new_dataset_required_fields(self, app):
        offset = h.url_for('dataset.new')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Create Dataset' in response.body
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        response = app.post(offset,
                            data=self._filled_dataset_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=False)

        offset = _get_relative_offset_from_response(response)
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Add data to the dataset' in response.body

        response = app.post(offset,
                            data=self._filled_resource_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=True)

        assert 'Resource added' in response.body


    def test_new_dataset_missing_fields(self, app):
        offset = h.url_for('dataset.new')
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

        offset = _get_relative_offset_from_response(response)
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


    def _filled_dataset_form(self):
        # type: () -> dict
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
        # type: () -> dict
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


@pytest.mark.usefixtures('with_request_context')
@pytest.mark.ckan_config("ckanext.canada.suppress_user_emails", True)
class TestNewUserWebForms(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestNewUserWebForms, self).setup_method(method)
        self.extra_environ_tester = {'REMOTE_USER': str(u""), 'REMOTE_ADDR': MOCK_IP_ADDRESS}
        self.extra_environ_tester_bad_ip = {'REMOTE_USER': str(u""), 'REMOTE_ADDR': '174.116.80.142'}
        self.org = Organization()


    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('builtins.open', mock_open_ip_list)
    def test_new_user_required_fields(self, app):
        offset = h.url_for('user.register')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Request an Account' in response.body

        response = app.post(offset,
                            data=self._filled_new_user_form(),
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=False)

        # test environ does not work with GET requests, use headers instead
        offset = _get_relative_offset_from_response(response)
        response = app.get(offset, headers={'X-Forwarded-For': MOCK_IP_ADDRESS})

        assert response.status_code == 200
        #FIXME: repoze handler in tests
        # assert 'Account Created' in response.body
        # assert 'Thank you for creating your account for the Open Government registry' in response.body


    @mock.patch('os.path.isfile', mock_isfile)
    @mock.patch('builtins.open', mock_open_ip_list)
    def test_new_user_missing_fields(self, app):
        offset = h.url_for('user.register')
        response = app.get(offset, extra_environ=self.extra_environ_tester)

        assert 'Request an Account' in response.body

        incomplete_new_user_form = {
            'phoneno': '1234567890',
            'password1': '',
            'password2': '',
            'save': ''
        }
        response = app.post(offset,
                            data=incomplete_new_user_form,
                            extra_environ=self.extra_environ_tester,
                            follow_redirects=True)

        assert 'The form contains invalid entries' in response.body
        assert 'Name: Missing value' in response.body
        assert 'Email: Missing value' in response.body
        assert 'Password: Please enter both passwords' in response.body


    def _filled_new_user_form(self):
        # type: () -> dict
        return {
            'name': 'newusername',
            'fullname': 'New User',
            'email': 'newuser@example.com',
            'department': self.org['id'],
            'phoneno': '1234567890',
            'password1': 'iptkH6kuctURRQadDBM0',  # security extension required good passphrase/password
            'password2': 'iptkH6kuctURRQadDBM0',  # security extension required good passphrase/password
            'save': ''
        }


@pytest.mark.usefixtures('with_request_context')
class TestRecombinantWebForms(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestRecombinantWebForms, self).setup_method(method)
        member = User()
        editor = User()
        sysadmin = Sysadmin()
        self.extra_environ_member = {'REMOTE_USER': member['name'].encode('ascii')}
        self.extra_environ_editor = {'REMOTE_USER': editor['name'].encode('ascii')}
        self.extra_environ_system = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        self.org = Organization(users=[{
            'name': member['name'],
            'capacity': 'member'},
            {'name': editor['name'],
             'capacity': 'editor'},
            {'name': sysadmin['name'],
             'capacity': 'admin'}],
            ati_email='test@example.com')
        self.pd_type = 'ati'
        self.nil_type = 'ati-nil'
        self.chromo = get_chromo(self.pd_type)
        self.nil_chromo = get_chromo(self.nil_type)
        self.fields = self.chromo['fields']
        self.nil_fields = self.nil_chromo['fields']
        self.example_record = self.chromo['examples']['record']
        self.example_nil_record = self.nil_chromo['examples']['record']


    def _lc_init_pd(self, org=None):
        # type: (Organization|None) -> None
        lc = LocalCKAN()
        org = org if org else self.org
        try:
            lc.action.recombinant_create(dataset_type=self.pd_type, owner_org=org['name'])
        except ValidationError:
            pass


    def _lc_create_pd_record(self, org=None, is_nil=False, return_field='name'):
        # type: (Organization|None, bool, str) -> str
        lc = LocalCKAN()
        org = org if org else self.org
        self._lc_init_pd(org=org)
        rval = lc.action.recombinant_show(dataset_type=self.pd_type, owner_org=org['name'])
        resource_id = rval['resources'][1]['id'] if is_nil else rval['resources'][0]['id']
        record = self.example_nil_record if is_nil else self.example_record
        lc.action.datastore_upsert(resource_id=resource_id, records=[record])
        return rval['resources'][1][return_field] if is_nil else rval['resources'][0][return_field]


    def _lc_pd_template(self, org=None):
        # type: (Organization|None) -> Workbook
        org = org if org else self.org
        self._lc_create_pd_record(org=org)
        self._lc_create_pd_record(org=org, is_nil=True)
        return excel_template(dataset_type=self.pd_type, org=org)


    def _lc_get_pd_package_id(self, org=None):
        # type: (Organization|None) -> str
        lc = LocalCKAN()
        org = org if org else self.org
        self._lc_init_pd(org=org)
        rval = lc.action.recombinant_show(dataset_type=self.pd_type, owner_org=org['name'])
        return rval['id']


    def test_member_cannot_init_pd(self, app):
        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_member)

        assert 'Create and update records' in response.body

        create_pd_form = {
            'create': ''
        }
        response = app.post(offset,
                            data=create_pd_form,
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'not authorized to add dataset' in response.body or \
               'not authorized to create packages' in response.body


    def test_editor_can_init_pd(self, app):
        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_editor)

        assert 'Create and update records' in response.body

        create_pd_form = {
            'create': ''
        }
        response = app.post(offset,
                            data=create_pd_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'Create and update multiple records' in response.body


    def test_admin_can_init_pd(self, app):
        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Create and update records' in response.body

        create_pd_form = {
            'create': ''
        }
        response = app.post(offset,
                            data=create_pd_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'Create and update multiple records' in response.body


    def test_ati_email_notice(self, app):
        no_ati_email_org = Organization(ati_email=None)
        self._lc_init_pd(org=no_ati_email_org)
        self._lc_init_pd()

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=no_ati_email_org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Your organization does not have an Access to Information email on file' in response.body

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Your organization does not have an Access to Information email on file' not in response.body
        assert 'Informal Requests for ATI Records Previously Released are being sent to' in response.body


    def test_member_cannot_create_single_record(self, app):
        self._lc_init_pd()

        offset = h.url_for('canada.create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        # members should not be able to acces create_pd_record endpoint
        response = app.get(offset, extra_environ=self.extra_environ_member, status=403)

        assert 'Unauthorized to create a resource for this package' in response.body

        pd_record_form = self._filled_create_single_record_form()
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'Unauthorized to create a resource for this package' in response.body


    def test_editor_can_create_single_record(self, app):
        self._lc_init_pd()

        offset = h.url_for('canada.create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_editor)

        assert 'Create Record' in response.body

        pd_record_form = self._filled_create_single_record_form()
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'Record Created' in response.body


    def test_admin_can_create_single_record(self, app):
        self._lc_init_pd()

        offset = h.url_for('canada.create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Create Record' in response.body

        pd_record_form = self._filled_create_single_record_form()
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'Record Created' in response.body


    def test_member_cannot_update_single_record(self, app):
        self._lc_create_pd_record()

        offset = h.url_for('canada.update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])
        # members should not be able to acces update_pd_record endpoint
        response = app.get(offset, extra_environ=self.extra_environ_member, status=403)

        assert 'Unauthorized to update dataset' in response.body

        pd_record_form = self._filled_create_single_record_form()
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'Unauthorized to update dataset' in response.body


    def test_editor_can_update_single_record(self, app):
        self._lc_create_pd_record()

        offset = h.url_for('canada.update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])
        response = app.get(offset, extra_environ=self.extra_environ_editor)

        assert 'Update Record' in response.body

        pd_record_form = self._filled_create_single_record_form()
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'Record {} Updated'.format(self.example_record['request_number']) in response.body


    def test_admin_can_update_single_record(self, app):
        self._lc_create_pd_record()

        offset = h.url_for('canada.update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Update Record' in response.body

        pd_record_form = self._filled_create_single_record_form()
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        response = app.post(offset,
                            data=pd_record_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'Record {} Updated'.format(self.example_record['request_number']) in response.body


    def _filled_create_single_record_form(self):
        # type: () -> dict
        return {
            'year': self.example_record['year'],
            'month': self.example_record['month'],
            'request_number': self.example_record['request_number'],
            'summary_en': self.example_record['summary_en'],
            'summary_fr': self.example_record['summary_fr'],
            'disposition': self.example_record['disposition'],
            'pages': self.example_record['pages'],
            'save': ''
        }


    def test_download_template(self, app):
        self._lc_create_pd_record()
        self._lc_create_pd_record(is_nil=True)

        offset = h.url_for('recombinant.template',
                           dataset_type=self.pd_type,
                           lang='en',
                           owner_org=self.org['name'])

        # members should be able to download template
        response = app.get(offset, extra_environ=self.extra_environ_member)
        template_file = BytesIO()
        # use get_data instead of body to avoid decoding issues. This is a file, we want bytes.
        template_file.write(response.get_data(as_text=False))
        # produces: (sheet-name, org-name, column_names, data_rows_generator)
        #   note: data_rows_generator excludes the example row
        template_file = list(read_excel(template_file))
        # pd workbook
        assert template_file[0][0] == self.pd_type  # check sheet name
        assert template_file[0][1] == self.org['name']  # check org name
        for f in self.fields:
            if f.get('import_template_include', True):  # only check fields included in template
                assert f['datastore_id'] in template_file[0][2]  # check each field id is in column names
        # nil workbook
        assert template_file[1][0] == self.nil_type  # check sheet name
        assert template_file[1][1] == self.org['name']  # check org name
        for f in self.nil_fields:
            if f.get('import_template_include', True):  # only check fields included in template
                assert f['datastore_id'] in template_file[1][2]  # check each field id is in column names


    def test_selected_download_template(self, app):
        resource_name = self._lc_create_pd_record()
        nil_resource_name = self._lc_create_pd_record(is_nil=True)

        offset = h.url_for('recombinant.template',
                           dataset_type=self.pd_type,
                           lang='en',
                           owner_org=self.org['name'])

        # members should be able to download template
        response = app.post(offset,
                            data={'resource_name': resource_name,
                                  'bulk-template': [self.example_record['request_number']]},
                            extra_environ=self.extra_environ_member)
        template_file = BytesIO()
        # use get_data instead of body to avoid decoding issues. This is a file, we want bytes.
        template_file.write(response.get_data(as_text=False))
        # produces: (sheet-name, org-name, column_names, data_rows_generator)
        #   note: data_rows_generator excludes the example row
        template_file = list(read_excel(template_file))
        # pd workbook
        assert template_file[0][0] == self.pd_type  # check sheet name
        assert template_file[0][1] == self.org['name']  # check org name
        for f in self.fields:
            if f.get('import_template_include', True):  # only check fields included in template
                assert f['datastore_id'] in template_file[0][2]  # check each field id is in column names
        for n, v in template_file[0][3]:
            assert n == DATA_FIRST_ROW
            assert int(v[0]) == int(self.example_record['year'])
            assert int(v[1]) == int(self.example_record['month'])
            assert v[2] == self.example_record['request_number']
            assert v[3] == self.example_record['summary_en']
            assert v[4] == self.example_record['summary_fr']
            assert v[5] == self.example_record['disposition']
            assert int(v[6]) == int(self.example_record['pages'])
            assert v[7] == self.example_record['comments_en']
            assert v[8] == self.example_record['comments_fr']
            break

        # members should be able to download template
        response = app.post(offset,
                            data={'resource_name': nil_resource_name,
                                  'bulk-template': [self.example_nil_record['year'], self.example_nil_record['month']]},
                            extra_environ=self.extra_environ_member)
        template_file = BytesIO()
        # use get_data instead of body to avoid decoding issues. This is a file, we want bytes.
        template_file.write(response.get_data(as_text=False))
        # produces: (sheet-name, org-name, column_names, data_rows_generator)
        #   note: data_rows_generator excludes the example row
        template_file = list(read_excel(template_file))
        # nil workbook
        assert template_file[1][0] == self.nil_type  # check sheet name
        assert template_file[1][1] == self.org['name']  # check org name
        for f in self.nil_fields:
            if f.get('import_template_include', True):  # only check fields included in template
                assert f['datastore_id'] in template_file[1][2]  # check each field id is in column names
        for n, v in template_file[1][3]:
            assert n == DATA_FIRST_ROW
            assert int(v[0]) == int(self.example_nil_record['year'])
            assert int(v[1]) == int(self.example_nil_record['month'])
            break


    def test_member_cannot_upload_records(self, app):
        template = self._lc_pd_template()
        template_file = self._populate_good_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_member)

        assert 'Create and update multiple records' not in response.body
        assert 'xls_update' not in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=template_file)
        response = app.post(form_action,
                     data=dataset_form,
                     extra_environ=self.extra_environ_member,
                     status=403,
                     follow_redirects=True)

        assert 'not authorized to update resource' in response.body


    def test_editor_can_upload_records(self, app):
        template = self._lc_pd_template()
        template_file = self._populate_good_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_editor)

        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=template_file)
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'Your file was successfully uploaded into the central system.' in response.body


    def test_admin_can_upload_records(self, app):
        template = self._lc_pd_template()
        template_file = self._populate_good_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=template_file)
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'Your file was successfully uploaded into the central system.' in response.body


    def test_member_cannot_validate_upload(self, app):
        template = self._lc_pd_template()
        good_template_file = self._populate_good_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_member)
        assert 'xls_update' not in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=good_template_file,
                                                action='validate')
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'not authorized to update resource' in response.body


    def test_editor_can_validate_upload(self, app):
        template = self._lc_pd_template()
        good_template_file = self._populate_good_template_file(template)
        bad_template_file = self._populate_bad_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_editor)

        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=bad_template_file,
                                                action='validate')
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'year: Please enter a valid year' in response.body
        assert 'month: Please enter a month number from 1-12' in response.body
        assert 'pages: This value must not be negative' in response.body

        dataset_form = self._filled_upload_form(filestream=good_template_file,
                                                action='validate')
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert 'No errors found.' in response.body


    def test_admin_can_validate_upload(self, app):
        template = self._lc_pd_template()
        good_template_file = self._populate_good_template_file(template)
        bad_template_file = self._populate_bad_template_file(template)

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_system)

        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.upload',
                                id=self._lc_get_pd_package_id())
        dataset_form = self._filled_upload_form(filestream=bad_template_file,
                                                action='validate')
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'year: Please enter a valid year' in response.body
        assert 'month: Please enter a month number from 1-12' in response.body
        assert 'pages: This value must not be negative' in response.body

        dataset_form = self._filled_upload_form(filestream=good_template_file,
                                                action='validate')
        response = app.post(form_action,
                            data=dataset_form,
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'No errors found.' in response.body


    def _populate_good_template_file(self, template):
        # type: (Workbook) -> BytesIO
        for i, v in enumerate(['2023',
                               '7',
                               'B-8019',
                               'This is an English Summary',
                               'This is a French Summary',
                               'DA',
                               '80',
                               'This is an English Comment',
                               'This is a French Comment']):
            fill_cell(sheet=template.active,
                      row=DATA_FIRST_ROW,
                      column=(i + DATA_FIRST_COL_NUM),
                      value=v,
                      style='reco_ref_value')
        good_template_file = BytesIO()
        template.save(good_template_file)
        good_template_file.seek(0, 0)
        return good_template_file


    def _populate_bad_template_file(self, template):
        # type: (Workbook) -> BytesIO
        for i, v in enumerate(['1978',
                               '20',
                               'B-8019',
                               'This is an English Summary',
                               'This is a French Summary',
                               'DA',
                               '-18',
                               'This is an English Comment',
                               'This is a French Comment']):
            fill_cell(sheet=template.active,
                      row=DATA_FIRST_ROW,
                      column=(i + DATA_FIRST_COL_NUM),
                      value=v,
                      style='reco_ref_value')
        bad_template_file = BytesIO()
        template.save(bad_template_file)
        bad_template_file.seek(0, 0)
        return bad_template_file


    def _filled_upload_form(self, filestream, action='upload'):
        # type: (BytesIO, str) -> dict
        return {
            'xls_update': (filestream, u'{}_en_{}.xlsx'.format(self.pd_type, self.org['name'])),
            action: ''
        }


    def test_member_cannot_delete_records(self, app):
        records_to_delete = self._prepare_records_to_delete()

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])
        response = app.get(offset, extra_environ=self.extra_environ_member)

        assert 'Create and update multiple records' not in response.body
        assert 'delete-form' not in response.body

        # members are no longer allowed to submit the bulk delete form
        form_action = h.url_for('recombinant.delete_records',
                                id=self._lc_get_pd_package_id(),
                                resource_id=records_to_delete['resource_id'])
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'not authorized to update resource' in response.body

        records_to_delete['form']['confirm'] = ''
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_member,
                            status=403,
                            follow_redirects=True)

        assert 'not authorized to update resource' in response.body


    def test_editor_can_delete_records(self, app):
        records_to_delete = self._prepare_records_to_delete()

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.delete_records',
                                id=self._lc_get_pd_package_id(),
                                resource_id=records_to_delete['resource_id'])
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=False)

        assert 'Confirm Delete' in response.body
        assert 'Are you sure you want to delete 2 records' in response.body

        records_to_delete['form']['confirm'] = ''
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_editor,
                            follow_redirects=True)

        assert '2 deleted.' in response.body


    def test_admin_can_delete_records(self, app):
        records_to_delete = self._prepare_records_to_delete()

        offset = h.url_for('recombinant.preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        form_action = h.url_for('recombinant.delete_records',
                                id=self._lc_get_pd_package_id(),
                                resource_id=records_to_delete['resource_id'])
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert 'Confirm Delete' in response.body
        assert 'Are you sure you want to delete 2 records' in response.body

        records_to_delete['form']['confirm'] = ''
        response = app.post(form_action,
                            data=records_to_delete['form'],
                            extra_environ=self.extra_environ_system,
                            follow_redirects=True)

        assert '2 deleted.' in response.body


    def _prepare_records_to_delete(self):
        # type: () -> dict
        original_request_number = self.example_record['request_number']
        self.example_record['request_number'] = 'B-8019'
        self._lc_create_pd_record()
        records_to_delete = self.example_record['request_number']
        # reset example record request number to original
        self.example_record['request_number'] = original_request_number
        resource_id = self._lc_create_pd_record(return_field='id')
        records_to_delete += '\n{}'.format(self.example_record['request_number'])
        return {
            'resource_id': resource_id,
            'form': {
                'bulk-delete': records_to_delete
            }
        }
