# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
import flask
import mock
import tempfile
from ckanapi import LocalCKAN

from ckan import model

import pytest
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)

from ckanext.recombinant.tables import get_chromo, get_geno
from ckanext.recombinant.views import _process_upload_file
from ckanext.recombinant.write_excel import excel_template, append_data
from ckanext.recombinant.errors import BadExcelData


# testing the upload of PD template files
# 'wrongdoing' PD template is used as an example here
@pytest.mark.usefixtures('with_request_context')
class TestXlsUpload(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestXlsUpload, self).setup_method(method)

        self.editor = User()
        self.extra_environ_tester = {'Authorization': self.editor['token']}
        self.environ_overrides_tester = {'REMOTE_USER': self.editor['name'].encode('ascii')}
        org = Organization(users=[
            {'name': self.editor['name'],
             'capacity': 'editor'}])
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='wrongdoing', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='wrongdoing', owner_org=org['name'])

        self.org = org
        self.pkg_id = rval['id']
        self.resource_id = rval['resources'][0]['id']

    def test_upload_empty(self):
        current_user = model.User.get(self.editor['name'])
        with mock.patch('ckan.lib.helpers.current_user', current_user):
            flask.g.user = self.editor['name']
            wb = excel_template('wrongdoing', self.org)
            f = tempfile.NamedTemporaryFile(suffix=".xlsx")
            wb.save(f.name)
            with pytest.raises(BadExcelData) as e:
                _process_upload_file(
                    self.lc,
                    self.lc.action.package_show(id=self.pkg_id),
                    f.name,
                    get_geno('wrongdoing'),
                    True)
            assert e.value.message == 'The template uploaded is empty'

    def test_upload_example(self):
        current_user = model.User.get(self.editor['name'])
        with mock.patch('ckan.lib.helpers.current_user', current_user):
            flask.g.user = self.editor['name']
            wb = excel_template('wrongdoing', self.org)
            f = tempfile.NamedTemporaryFile(suffix=".xlsx")

            # Enter the example record into the excel template
            record = get_chromo('wrongdoing')['examples']['record']
            wb = append_data(wb, [record], get_chromo('wrongdoing'))
            wb.save(f.name)

            _process_upload_file(
                self.lc,
                self.lc.action.package_show(id=self.pkg_id),
                f.name,
                get_geno('wrongdoing'),
                False)

        result = self.lc.action.datastore_search(resource_id=self.resource_id)
        records = result.get('records')
        assert records

        # we already have test coverage for record_created, record_modified, and user_modified
        # in test_tiggers. So we can just exclude them here to make datetime things easier.
        expected_records = [{
           "_id": 1,
           "ref_number": "1980198",
           "file_id_number": "15677",
           "file_id_date": "2016-01-01",
           "case_description_en": "Description",
           "case_description_fr": "Description",
           "findings_conclusions": ["b"],
           "recommendations_corrective_measures_en": "Recommendations and Corrective Measures",
           "recommendations_corrective_measures_fr": "Recommandations et mesures correctives",
           # "record_created": "2024-07-10T19:57:55",
           # "record_modified": "2024-07-10T19:57:55",
           # "user_modified": "registry"
        }]
        for record in records:
            record.pop('record_created', None)
            record.pop('record_modified', None)
            record.pop('user_modified', None)

        assert records == expected_records

    def test_upload_example_dry_run(self):
        current_user = model.User.get(self.editor['name'])
        with mock.patch('ckan.lib.helpers.current_user', current_user):
            flask.g.user = self.editor['name']
            wb = excel_template('wrongdoing', self.org)
            f = tempfile.NamedTemporaryFile(suffix=".xlsx")

            # Enter the example record into the excel template
            record = get_chromo('wrongdoing')['examples']['record']
            wb = append_data(wb, [record], get_chromo('wrongdoing'))
            wb.save(f.name)

            _process_upload_file(
                self.lc,
                self.lc.action.package_show(id=self.pkg_id),
                f.name,
                get_geno('wrongdoing'),
                True)

        result = self.lc.action.datastore_search(resource_id=self.resource_id)
        records = result.get('records')
        assert records == []

    def test_upload_wrong_type(self):
        flask.g.user = self.editor['name']
        wb = excel_template('travela', self.org)
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        wb.save(f.name)
        with pytest.raises(BadExcelData) as e:
            _process_upload_file(
                self.lc,
                self.lc.action.package_show(id=self.pkg_id),
                f.name,
                get_geno('wrongdoing'),
                True)
        assert e.value.message == 'Invalid file for this data type. Sheet must be labeled "wrongdoing", but you supplied a sheet labeled "travela"'
