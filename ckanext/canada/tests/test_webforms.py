# -*- coding: UTF-8 -*-
from nose.tools import assert_raises
from nose import SkipTest
from ckan.lib.helpers import url_for
from ckanapi import (
    LocalCKAN,
    NotAuthorized
)

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)
from ckan.tests.helpers import FunctionalTestBase

from ckanext.recombinant.tables import get_chromo


class TestPackageWebForms(FunctionalTestBase):
    def setup(self):
        super(TestPackageWebForms, self).setup()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.app = self._get_test_app()


    def test_new_dataset_required_fields(self):
        offset = url_for(controller='package', action='new')

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
        offset = url_for(controller='package', action='new')

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
        super(TestNewUserWebForms, self).setup()
        self.org = Organization()
        self.app = self._get_test_app()


    def test_new_user_required_fields(self):
        offset = url_for(controller='user', action='register')

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
        offset = url_for(controller='user', action='register')

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
        self.example_record = get_chromo(self.pd_type)['examples']['record']
        self.app = self._get_test_app()


    def lc_init_pd(self, org):
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type=self.pd_type, owner_org=org['name'])


    def lc_create_pd_record(self, org):
        lc = LocalCKAN()
        self.lc_init_pd(org=org)
        rval = lc.action.recombinant_show(dataset_type=self.pd_type, owner_org=org['name'])
        resource_id = rval['resources'][0]['id']
        lc.action.datastore_upsert(resource_id=resource_id, records=[self.example_record])
        return self.example_record['request_number']


    def test_member_cannot_init_pd(self):
        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
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
        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
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
        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
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
        self.lc_init_pd(org=self.org)

        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
                         action='preview_table',
                         resource_name=self.pd_type,
                         owner_org=no_ati_email_org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Your organization does not have an Access to Information email on file' in response.body

        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
                         action='preview_table',
                         resource_name=self.pd_type,
                         owner_org=self.org['name'])

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Your organization does not have an Access to Information email on file' not in response.body
        assert 'Informal Requests for ATI Records Previously Released are being sent to' in response.body


    def test_member_cannot_create_single_record(self):
        self.lc_init_pd(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
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
        self.lc_init_pd(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
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
        self.lc_init_pd(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
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
        rid = self.lc_create_pd_record(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
                         action='update_pd_record',
                         resource_name=self.pd_type,
                         owner_org=self.org['name'],
                         pk=rid)

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
        rid = self.lc_create_pd_record(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
                         action='update_pd_record',
                         resource_name=self.pd_type,
                         owner_org=self.org['name'],
                         pk=rid)

        response = self.app.get(offset, extra_environ=self.extra_environ_editor)
        assert 'Update Record' in response.body

        pd_record_form = response.forms['update_pd_record']
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_editor)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_editor)
        assert 'Record {} Updated'.format(rid) in response.body


    def test_admin_can_update_single_record(self):
        rid = self.lc_create_pd_record(org=self.org)

        offset = url_for(controller='ckanext.canada.controller:PDUpdateController',
                         action='update_pd_record',
                         resource_name=self.pd_type,
                         owner_org=self.org['name'],
                         pk=rid)

        response = self.app.get(offset, extra_environ=self.extra_environ_system)
        assert 'Update Record' in response.body

        pd_record_form = response.forms['update_pd_record']
        pd_record_form['summary_en'] = 'New Summary EN'
        pd_record_form['summary_fr'] = 'New Summary FR'
        # Submit
        response = pd_record_form.submit('save', extra_environ=self.extra_environ_system)

        response = self.app.get(response.headers['Location'], extra_environ=self.extra_environ_system)
        assert 'Record {} Updated'.format(rid) in response.body


    def filled_create_single_record_form(self, response):
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
        raise SkipTest("TODO: Implement test for downloading template file.")
        # ckanext.recombinant.controller:UploadController -> template
        # (dataset_type, lang, owner_org)
        from logging import getLogger
        from pprint import pprint
        log = getLogger(__name__)
        log.info("    ")
        log.info("DEBUGGING::")
        log.info("")
        log.info("    ")


    def test_upload_multiple(self):
        raise SkipTest("TODO: Implement test for uploading filled template file.")
        # ckanext.recombinant.controller:UploadController -> preview_table
        # (resource_name, owner_org)
        # forms['dataset-form'] -> ['xls_update'] -> 'upload'


    def test_upload_validation(self):
        raise SkipTest("TODO: Implement test for validating filled template file.")
        # ckanext.recombinant.controller:UploadController -> preview_table
        # (resource_name, owner_org)
        # forms['dataset-form'] -> ['xls_update'] -> 'validate'


    def test_delete_records(self):
        raise SkipTest("TODO: Implement test for deleting records.")
        # ckanext.recombinant.controller:UploadController -> preview_table
        # (resource_name, owner_org)
        # forms['delete-form'] -> ['bulk-delete'] -> ''
