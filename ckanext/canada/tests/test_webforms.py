# -*- coding: UTF-8 -*-
from bs4 import BeautifulSoup
import pytest
from ckan.lib.helpers import url_for

from ckan.tests.helpers import reset_db, _get_test_app

from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import CanadaOrganization as Organization


@pytest.mark.usefixtures('with_request_context')
class TestWebForms(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before all test methods of the class are called.
        Setup any state specific to the execution of the given class (which usually contains tests).
        """
        reset_db()
        self.sysadmin = Sysadmin()
        self.extra_environ_tester = {'REMOTE_USER': self.sysadmin['name'].encode('ascii')}
        self.org = Organization()
        self.app = _get_test_app()


    def test_new_dataset_required_fields(self):
        pytest.skip('TODO: implement test for ckan 2.9')
        offset = url_for('dataset.new')

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
        pytest.skip('TODO: implement test for ckan 2.9')
        offset = url_for('dataset.new')

        # test first form, creating a dataset
        response = self.app.get(offset, extra_environ=self.extra_environ_tester)
        # test if the page has the Create Dataset heading or title
        assert 'Create Dataset' in response.body
        # test if the page has the create org warning
        assert 'Before you can create a dataset you need to create an organization' not in response.body

        dataset_form = BeautifulSoup(response.data).body.select("form#dataset-edit")
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
        resource_form = BeautifulSoup(response.data).body.select("form#resource-edit")
        resource_form['url'] = 'somewhere'
        # Submit
        response = resource_form.submit('save', 2, extra_environ=self.extra_environ_tester)

        assert 'Error' in response
        assert 'Title (English): Missing value' in response
        assert 'Title (French): Missing value' in response
        assert 'Resource Type: Missing value' in response
        assert 'Format: Missing value' in response


    def filled_dataset_form(self, response):
        dataset_form = BeautifulSoup(response.data).body.select("form#dataset-edit")
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
        resource_form = BeautifulSoup(response.data).body.select("form#resource-edit")
        resource_form['name_translated-en'] = 'english resource name'
        resource_form['name_translated-fr'] = 'french resource name'
        resource_form['resource_type'] = 'dataset'
        resource_form['url'] = 'somewhere'
        resource_form['format'] = 'CSV'
        resource_form['language'] = 'en'
        return resource_form

