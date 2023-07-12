# -*- coding: UTF-8 -*-
from StringIO import StringIO
from openpyxl.workbook import Workbook
from webtest import Text, Form, TestResponse
from nose.tools import assert_raises
from ckan.plugins.toolkit import h
from ckanapi import (
    LocalCKAN,
    NotAuthorized,
    ValidationError
)

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)
from ckan.tests.helpers import FunctionalTestBase

from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.read_excel import read_excel
from ckanext.recombinant.write_excel import (
    excel_template,
    fill_cell,
    DATA_FIRST_ROW,
    DATA_FIRST_COL_NUM
)
from ckanext.canada.tests import canada_tests_init_validation


class TestPackageWebForms(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestPackageWebForms, self).setup()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.app = self._get_test_app()


    def test_new_dataset_required_fields(self):
        offset = h.url_for(controller='package', action='new')

        # test first form, creating a dataset
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)
        # test if the page has the Create Dataset heading or title
        assert 'Create Dataset' in response.body
        # test if the page has the create org warning
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        dataset_form = self.filled_dataset_form(response)
        # Submit
        response = dataset_form.submit('save', extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'Error' in response

        # test second form, creating a resource for the above dataset
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_tester)
        resource_form = self.filled_resource_form(response)
        # Submit
        response = resource_form.submit('save', 2, extra_environ=self.extra_environ_tester)

        # Check resource page
        assert not 'Error' in response


    def test_new_dataset_missing_fields(self):
        offset = h.url_for(controller='package', action='new')

        # test first form, creating a dataset
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)
        # test if the page has the Create Dataset heading or title
        assert 'Create Dataset' in response.body
        # test if the page has the create org warning
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        dataset_form = response.forms['dataset-edit']
        dataset_form['owner_org'] = self.org['id']
        # Submit
        response = dataset_form.submit('save', extra_environ=self.extra_environ_tester)

        assert 'Error' in response
        assert 'Title (French): Missing value' in response
        #FIXME: subject error not showing up in response body
        #assert 'Subject: Select at least one' in response
        assert 'Title (English): Missing value' in response
        assert 'Description (English): Missing value' in response
        assert 'Description (French): Missing value' in response
        assert 'Keywords (English): Missing value' in response
        assert 'Keywords (French): Missing value' in response
        assert 'Date Published: Missing value' in response
        assert 'Frequency: Missing value' in response
        assert 'Approval: Missing value' in response
        assert 'Date Published: Missing value' in response
        assert 'Ready to Publish: Missing value' in response

        dataset_form = self.filled_dataset_form(response)
        # Submit filled form to continue onto the resource edit form
        response = dataset_form.submit('save', extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'Error' in response

        # test second form, creating a resource for the above dataset
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_tester)
        resource_form = response.forms['resource-edit']
        resource_form['url'] = 'somewhere'
        # Submit
        response = resource_form.submit('save', 2, extra_environ=self.extra_environ_tester)

        assert 'Error' in response
        assert 'Title (English): Missing value' in response
        assert 'Title (French): Missing value' in response
        assert 'Resource Type: Missing value' in response
        assert 'Format: Missing value' in response


    def filled_dataset_form(self, response):
        # type: (TestResponse) -> Form
        dataset_form = response.forms['dataset-edit']
        dataset_form['owner_org'] = self.org['id']
        dataset_form['title_translated-en'] = 'english title'
        dataset_form['title_translated-fr'] = 'french title'
        dataset_form['notes_translated-en'] = 'english description'
        dataset_form['notes_translated-fr'] = 'french description'
        dataset_form['subject'] = 'arts_music_literature'
        dataset_form['keywords-en'] = 'english keywords'
        dataset_form['keywords-fr'] = 'french keywords'
        dataset_form['date_published'] = '2000-01-01'
        dataset_form['ready_to_publish'] = 'false'
        dataset_form['frequency'] = 'as_needed'
        dataset_form['jurisdiction'] = 'federal'
        dataset_form['license_id'] = 'ca-ogl-lgo'
        dataset_form['restrictions'] = 'unrestricted'
        dataset_form['imso_approval'] = 'true'
        return dataset_form


    def filled_resource_form(self, response):
        # type: (TestResponse) -> Form
        resource_form = response.forms['resource-edit']
        resource_form['name_translated-en'] = 'english resource name'
        resource_form['name_translated-fr'] = 'french resource name'
        resource_form['resource_type'] = 'dataset'
        resource_form['url'] = 'somewhere'
        resource_form['format'] = 'CSV'
        resource_form['language'] = 'en'
        return resource_form


class TestNewUserWebForms(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestNewUserWebForms, self).setup()
        self.org = Organization()
        self.app = self._get_test_app()


    def test_new_user_required_fields(self):
        offset = h.url_for(controller='user', action='register')

        # test form, registering new user account
        response = self.app.get(offset)
        # test if the page has the Request an Account heading or title
        assert 'Request an Account' in response.body

        new_user_form = self.filled_new_user_form(response)
        # Submit
        response = new_user_form.submit('save')

        # Check response page
        assert not 'Error' in response


    def test_new_user_missing_fields(self):
        offset = h.url_for(controller='user', action='register')

        # test form, registering new user account
        response = self.app.get(offset)
        # test if the page has the Request an Account heading or title
        assert 'Request an Account' in response.body

        new_user_form = response.forms['user-register-form']
        new_user_form['phoneno'] = '1234567890'
        # Submit
        response = new_user_form.submit('save')

        assert 'The form contains invalid entries' in response
        assert 'Name: Missing value' in response
        assert 'Email: Missing value' in response
        assert 'Password: Please enter both passwords' in response


    def filled_new_user_form(self, response):
        # type: (TestResponse) -> Form
        new_user_form = response.forms['user-register-form']
        new_user_form['name'] = 'newusername'
        new_user_form['fullname'] = 'New User'
        new_user_form['email'] = 'newuser@example.com'
        new_user_form['department'] = self.org['id']
        new_user_form['phoneno'] = '1234567890'
        new_user_form['password1'] = 'thisisapassword'
        new_user_form['password2'] = 'thisisapassword'
        return new_user_form


class TestRecombinantWebForms(FunctionalTestBase):
    def setup(self):
        canada_tests_init_validation()
        super(TestRecombinantWebForms, self).setup()
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
        self.app = self._get_test_app()


    def lc_init_pd(self, org=None):
        # type: (Organization|None) -> None
        lc = LocalCKAN()
        org = org if org else self.org
        try:
            lc.action.recombinant_create(dataset_type=self.pd_type, owner_org=org['name'])
        except ValidationError:
            pass


    def lc_create_pd_record(self, org=None, is_nil=False):
        # type: (Organization|None, bool) -> str
        lc = LocalCKAN()
        org = org if org else self.org
        self.lc_init_pd(org=org)
        rval = lc.action.recombinant_show(dataset_type=self.pd_type, owner_org=org['name'])
        resource_id = rval['resources'][1]['id'] if is_nil else rval['resources'][0]['id']
        record = self.example_nil_record if is_nil else self.example_record
        lc.action.datastore_upsert(resource_id=resource_id, records=[record])
        return rval['resources'][1]['name'] if is_nil else rval['resources'][0]['name']


    def lc_pd_template(self, org=None):
        # type: (Organization|None) -> Workbook
        org = org if org else self.org
        self.lc_create_pd_record(org=org)
        self.lc_create_pd_record(org=org, is_nil=True)
        return excel_template(dataset_type=self.pd_type, org=org)


    def test_member_cannot_init_pd(self):
        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        # test form, initializing new pd resource
        response = self.app.get(offset, extra_environ=self.extra_environ_member)
        # test if the page has the Create and update records heading or title
        assert 'Create and update records' in response.body

        registration_form = response.forms['create-pd-resource']
        # Submit
        assert_raises(NotAuthorized,
                      registration_form.submit,
                      'create',
                      extra_environ=self.extra_environ_member)


    def test_editor_can_init_pd(self):
        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        # test form, initializing new pd resource
        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        # test if the page has the Create and update records heading or title
        assert 'Create and update records' in response.body

        registration_form = response.forms['create-pd-resource']
        # Submit
        response = registration_form.submit('create', extra_environ=self.extra_environ_editor)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor)
        assert 'Create and update multiple records' in response.body


    def test_admin_can_init_pd(self):
        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        # test form, initializing new pd resource
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        # test if the page has the Create and update records heading or title
        assert 'Create and update records' in response.body

        registration_form = response.forms['create-pd-resource']
        # Submit
        response = registration_form.submit('create', extra_environ=self.extra_environ_system)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body


    def test_ati_email_notice(self):
        no_ati_email_org = Organization(ati_email=None)
        self.lc_init_pd(org=no_ati_email_org)
        self.lc_init_pd()

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=no_ati_email_org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Your organization does not have an Access to Information email on file' in response.body

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Your organization does not have an Access to Information email on file' not in response.body
        assert 'Informal Requests for ATI Records Previously Released are being sent to' in response.body
        assert self.org['ati_email'].encode() in response.body


    def test_member_cannot_create_single_record(self):
        self.lc_init_pd()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        # members should not be able to acces create_pd_record endpoint
        response = self.app.get(offset, extra_environ=self.extra_environ_member, status=403)
        assert 'Access was denied to this resource' in response.body

        # use sysadmin to get page for permission reasons
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create Record' in response.body

        pd_record_form = self.filled_create_single_record_form(response)
        # Submit as member
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_member, status=403)
        assert 'Access was denied to this resource' in response.body


    def test_editor_can_create_single_record(self):
        self.lc_init_pd()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Create Record' in response.body

        pd_record_form = self.filled_create_single_record_form(response)
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_editor)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor)
        assert 'Record Created' in response.body


    def test_admin_can_create_single_record(self):
        self.lc_init_pd()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='create_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create Record' in response.body

        pd_record_form = self.filled_create_single_record_form(response)
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_system)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system)
        assert 'Record Created' in response.body


    def test_member_cannot_update_single_record(self):
        self.lc_create_pd_record()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])

        # members should not be able to acces update_pd_record endpoint
        response = self.app.get(offset, extra_environ=self.extra_environ_member, status=403)
        assert 'Access was denied to this resource' in response.body

        # use sysadmin to get page for permission reasons
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Update Record' in response.body

        pd_record_form = response.forms['update_pd_record']
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        # Submit as member
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_member, status=403)
        assert 'Access was denied to this resource' in response.body


    def test_editor_can_update_single_record(self):
        self.lc_create_pd_record()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Update Record' in response.body

        pd_record_form = response.forms['update_pd_record']
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_editor)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor)
        assert 'Record {} Updated'.format(self.example_record['request_number']) in response.body


    def test_admin_can_update_single_record(self):
        self.lc_create_pd_record()

        offset = h.url_for(controller='ckanext.canada.controller:PDUpdateController',
                           action='update_pd_record',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'],
                           pk=self.example_record['request_number'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Update Record' in response.body

        pd_record_form = response.forms['update_pd_record']
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_system)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system)
        assert 'Record {} Updated'.format(self.example_record['request_number']) in response.body


    def filled_create_single_record_form(self, response):
        # type: (TestResponse) -> Form
        pd_record_form = response.forms['create_pd_record']
        pd_record_form['year'] = self.example_record['year']
        pd_record_form['month'] = self.example_record['month']
        pd_record_form['request_number'] = self.example_record['request_number']
        pd_record_form['summary_en'] = self.example_record['summary_en']
        pd_record_form['summary_fr'] = self.example_record['summary_fr']
        pd_record_form['disposition'] = self.example_record['disposition']
        pd_record_form['pages'] = self.example_record['pages']
        return pd_record_form


    def test_download_template(self):
        self.lc_create_pd_record()
        self.lc_create_pd_record(is_nil=True)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='template',
                           dataset_type=self.pd_type,
                           lang='en',
                           owner_org=self.org['name'])

        # members should be able to download template
        response = self.app.get(offset, extra_environ=self.extra_environ_member)
        template_file = StringIO()
        template_file.write(response.body)
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


    def test_selected_download_template(self):
        resource_name = self.lc_create_pd_record()
        nil_resource_name = self.lc_create_pd_record(is_nil=True)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='template',
                           dataset_type=self.pd_type,
                           lang='en',
                           owner_org=self.org['name'])

        # members should be able to download template
        response = self.app.post(offset,
                                 {'resource_name': resource_name,
                                  'bulk-template': [self.example_record['request_number']]},
                                 extra_environ=self.extra_environ_member)
        template_file = StringIO()
        template_file.write(response.body)
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
        response = self.app.post(offset,
                                 {'resource_name': nil_resource_name,
                                  'bulk-template': [self.example_nil_record['year'], self.example_nil_record['month']]},
                                 extra_environ=self.extra_environ_member)
        template_file = StringIO()
        template_file.write(response.body)
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


    def test_member_cannot_upload_records(self):
        template = self.lc_pd_template()
        template_file = self.populate_good_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_member)
        assert 'Create and update multiple records' not in response.body
        # the `dataset-form` html form tag is still rendered
        # as it contains other elements, but should not contain
        # the upload fields for a member
        dataset_form = response.forms['dataset-form']
        assert 'xls_update' not in dataset_form.fields

        # use sysadmin to get page for permission reasons
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        # Submit
        assert_raises(NotAuthorized,
                      dataset_form.submit,
                      upload_files=[('xls_update',
                                     '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                     template_file.read())],
                      extra_environ=self.extra_environ_member,
                      status=403)


    def test_editor_can_upload_records(self):
        template = self.lc_pd_template()
        template_file = self.populate_good_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      template_file.read())],
                                       extra_environ=self.extra_environ_editor)

        # recombinant returns package.read url, which redirects in recombinant, thus the extra follow()
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor).follow(extra_environ=self.extra_environ_editor)
        assert 'Your file was successfully uploaded into the central system.' in response.body


    def test_admin_can_upload_records(self):
        template = self.lc_pd_template()
        template_file = self.populate_good_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      template_file.read())],
                                       extra_environ=self.extra_environ_system)

        # recombinant returns package.read url, which redirects in recombinant, thus the extra follow()
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system).follow(extra_environ=self.extra_environ_system)
        assert 'Your file was successfully uploaded into the central system.' in response.body


    def test_member_cannot_validate_upload(self):
        template = self.lc_pd_template()
        good_template_file = self.populate_good_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_member)
        # the `dataset-form` html form tag is still rendered
        # as it contains other elements, but should not contain
        # the upload fields for a member
        dataset_form = response.forms['dataset-form']
        assert 'xls_update' not in dataset_form.fields

        # use sysadmin to get page for permission reasons
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        dataset_form = self.webtest_validate_post_fix(dataset_form)  # adds `validate` to POST body
        # Submit
        assert_raises(NotAuthorized,
                      dataset_form.submit,
                      upload_files=[('xls_update',
                                     '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                     good_template_file.read())],
                      extra_environ=self.extra_environ_member,
                      status=403)


    def test_editor_can_validate_upload(self):
        template = self.lc_pd_template()
        good_template_file = self.populate_good_template_file(template)
        bad_template_file = self.populate_bad_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        dataset_form = self.webtest_validate_post_fix(dataset_form)
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      bad_template_file.read())],
                                       extra_environ=self.extra_environ_editor)

        assert 'year: Please enter a valid year' in response.body
        assert 'month: Please enter a month number from 1-12' in response.body
        assert 'pages: This value must not be negative' in response.body

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)

        dataset_form = response.forms['dataset-form']
        dataset_form = self.webtest_validate_post_fix(dataset_form)  # adds `validate` to POST body
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      good_template_file.read())],
                                       extra_environ=self.extra_environ_editor)

        # recombinant returns package.read url, which redirects in recombinant, thus the extra follow()
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor).follow(extra_environ=self.extra_environ_editor)
        assert 'No errors found.' in response.body


    def test_admin_can_validate_upload(self):
        template = self.lc_pd_template()
        good_template_file = self.populate_good_template_file(template)
        bad_template_file = self.populate_bad_template_file(template)

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        dataset_form = response.forms['dataset-form']
        dataset_form = self.webtest_validate_post_fix(dataset_form)  # adds `validate` to POST body
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      bad_template_file.read())],
                                       extra_environ=self.extra_environ_system)

        assert 'year: Please enter a valid year' in response.body
        assert 'month: Please enter a month number from 1-12' in response.body
        assert 'pages: This value must not be negative' in response.body

        response = self.app.get(offset, extra_environ=self.extra_environ_system)

        dataset_form = response.forms['dataset-form']
        dataset_form = self.webtest_validate_post_fix(dataset_form)
        # Submit
        response = dataset_form.submit(upload_files=[('xls_update',
                                                      '{}_en_{}.xlsx'.format(self.pd_type, self.org['name']),
                                                      good_template_file.read())],
                                       extra_environ=self.extra_environ_system)

        # recombinant returns package.read url, which redirects in recombinant, thus the extra follow()
        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system).follow(extra_environ=self.extra_environ_system)
        assert 'No errors found.' in response.body


    def populate_good_template_file(self, template):
        # type: (Workbook) -> StringIO
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
        good_template_file = StringIO()
        template.save(good_template_file)
        good_template_file.seek(0, 0)
        return good_template_file


    def populate_bad_template_file(self, template):
        # type: (Workbook) -> StringIO
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
        bad_template_file = StringIO()
        template.save(bad_template_file)
        bad_template_file.seek(0, 0)
        return bad_template_file


    def webtest_validate_post_fix(self, form):
        # type: (Form) -> Form

        # webtest field for validate
        # because recombinant checks POST['validate']
        # and webtest does not add submit fields to POST.
        # This replaces submitting the form with the validate
        # submit input index.
        validate_field = Text(form, 'input', None, None, '1')
        form.fields['validate'] = [validate_field]
        form.field_order.append(('validate', validate_field))
        return form


    def test_member_cannot_delete_records(self):
        original_request_number = self.example_record['request_number']
        self.example_record['request_number'] = 'B-8019'
        self.lc_create_pd_record()
        records_to_delete = self.example_record['request_number']
        # reset example record request number to original
        self.example_record['request_number'] = original_request_number
        self.lc_create_pd_record()
        records_to_delete += '\n{}'.format(self.example_record['request_number'])

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_member)
        assert 'Create and update multiple records' not in response.body
        assert 'delete-form' not in response.forms

        # use sysadmin to get page for permission reasons
        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        delete_form = response.forms['delete-form']
        delete_form['bulk-delete'] = records_to_delete
        # Submit
        # members are allowed to submit the bulk delete form
        # as it will ask for confirmation of the delete
        response = delete_form.submit(extra_environ=self.extra_environ_member)
        assert 'Confirm Delete' in response.body
        assert 'Are you sure you want to delete 2 records' in response.body

        confirm_form = response.forms['recombinant-confirm-delete-form']
        # Submit
        assert_raises(NotAuthorized,
                      confirm_form.submit,
                      'confirm',
                      extra_environ=self.extra_environ_member)


    def test_editor_can_delete_records(self):
        original_request_number = self.example_record['request_number']
        self.example_record['request_number'] = 'B-8019'
        self.lc_create_pd_record()
        records_to_delete = self.example_record['request_number']
        # reset example record request number to original
        self.example_record['request_number'] = original_request_number
        self.lc_create_pd_record()
        records_to_delete += '\n{}'.format(self.example_record['request_number'])

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Create and update multiple records' in response.body

        delete_form = response.forms['delete-form']
        delete_form['bulk-delete'] = records_to_delete
        # Submit
        response = delete_form.submit(extra_environ=self.extra_environ_editor)

        assert 'Confirm Delete' in response.body
        assert 'Are you sure you want to delete 2 records' in response.body

        confirm_form = response.forms['recombinant-confirm-delete-form']
        # Submit
        response = confirm_form.submit('confirm', extra_environ=self.extra_environ_editor)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor)
        assert '2 deleted.' in response.body


    def test_admin_can_delete_records(self):
        original_request_number = self.example_record['request_number']
        self.example_record['request_number'] = 'B-8019'
        self.lc_create_pd_record()
        records_to_delete = self.example_record['request_number']
        # reset example record request number to original
        self.example_record['request_number'] = original_request_number
        self.lc_create_pd_record()
        records_to_delete += '\n{}'.format(self.example_record['request_number'])

        offset = h.url_for(controller='ckanext.recombinant.controller:UploadController',
                           action='preview_table',
                           resource_name=self.pd_type,
                           owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Create and update multiple records' in response.body

        delete_form = response.forms['delete-form']
        delete_form['bulk-delete'] = records_to_delete
        # Submit
        response = delete_form.submit(extra_environ=self.extra_environ_system)

        assert 'Confirm Delete' in response.body
        assert 'Are you sure you want to delete 2 records' in response.body

        confirm_form = response.forms['recombinant-confirm-delete-form']
        # Submit
        response = confirm_form.submit('confirm', extra_environ=self.extra_environ_system)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system)
        assert '2 deleted.' in response.body
