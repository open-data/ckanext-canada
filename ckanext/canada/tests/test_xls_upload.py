# -*- coding: UTF-8 -*-
import os
import tempfile
from nose.tools import assert_equal, assert_raises
from ckanapi import LocalCKAN

from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import Organization

from ckanext.recombinant.tables import get_chromo, get_geno
from ckanext.recombinant.controller import _process_upload_file
from ckanext.recombinant.write_excel import excel_template, append_data
from ckanext.recombinant.errors import  BadExcelData
from openpyxl import load_workbook, Workbook


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


# testing the upload of PD template files
# 'wrongdoing' PD template is used as an example here
class TestXlsUpload(FunctionalTestBase):
    def setup(self):
        super(TestXlsUpload, self).setup()
        self.org = Organization()
        lc = LocalCKAN()
        lc.action.recombinant_create(dataset_type='wrongdoing', owner_org=self.org['name'])
        rval = lc.action.recombinant_show(dataset_type='wrongdoing', owner_org=self.org['name'])
        self.pkg_id = rval['id']

    
    def test_upload_empty(self):
        lc = LocalCKAN()
        wb = excel_template('wrongdoing', self.org)
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        wb.save(f.name)
        with assert_raises(BadExcelData) as e:
            _process_upload_file(
                lc,
                lc.action.package_show(id=self.pkg_id),
                f.name,
                get_geno('wrongdoing'),
                True)
        assert_equal('The template uploaded is empty', e.exception.message)


    def test_upload_example(self):
        lc = LocalCKAN()
        wb = excel_template('wrongdoing', self.org)
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")

        # Enter the example record into the excel template
        record = get_chromo('wrongdoing')['examples']['record']
        wb = append_data(wb, [record], get_chromo('wrongdoing'))
        wb.save(f.name)

        _process_upload_file(
            lc,
            lc.action.package_show(id=self.pkg_id),
            f.name,
            get_geno('wrongdoing'),
            True)


    def test_upload_wrong_type(self):
        lc = LocalCKAN()
        wb = excel_template('travela', self.org)
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        wb.save(f.name)
        with assert_raises(BadExcelData) as e:
            _process_upload_file(
                lc,
                lc.action.package_show(id=self.pkg_id),
                f.name,
                get_geno('wrongdoing'),
                True)
        assert_equal('Invalid file for this data type. Sheet must be labeled "wrongdoing", but you supplied a sheet labeled "travela"',
            e.exception.message)

        
        

    
            
