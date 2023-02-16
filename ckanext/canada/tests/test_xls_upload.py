# -*- coding: UTF-8 -*-
import tempfile
from ckanapi import LocalCKAN

import pytest
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanext.recombinant.tables import get_chromo, get_geno
from ckanext.recombinant.views import _process_upload_file
from ckanext.recombinant.write_excel import excel_template, append_data
from ckanext.recombinant.errors import  BadExcelData
from openpyxl import load_workbook, Workbook


# testing the upload of PD template files
# 'wrongdoing' PD template is used as an example here
class TestXlsUpload(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()

        org = Organization()
        self.lc = LocalCKAN()

        self.lc.action.recombinant_create(dataset_type='wrongdoing', owner_org=org['name'])
        rval = self.lc.action.recombinant_show(dataset_type='wrongdoing', owner_org=org['name'])

        self.org = org
        self.pkg_id = rval['id']


    def test_upload_empty(self):
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


    def test_upload_wrong_type(self):
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
