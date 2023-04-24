# -*- coding: UTF-8 -*-
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import url_for

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)
from ckan.tests.helpers import FunctionalTestBase


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
             'capacity': 'admin'}])
        self.pd_type = 'ati'
        self.app = self._get_test_app()


    def test_member_cannot_init_pd(self):
        offset = url_for(controller='ckanext.recombinant.controller:UploadController',
                         action='preview_table',
                         resource_name=self.pd_type,
                         owner_org=self.org['name'])

        # test form, initializing new pd resource
        response = self.app.get(offset)
        # test if the page has the Create and update records heading or title
        #FIXME: assert headings...
        assert 'Create and update records' in response

        registration_form = response.forms['create-pd-resource']
        # Submit
        response = registration_form.submit('create', extra_environ=self.extra_environ_member)
        #TODO: assert validation error??
        assert True
