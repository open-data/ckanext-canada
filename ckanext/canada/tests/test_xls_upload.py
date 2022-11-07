# -*- coding: UTF-8 -*-
import tempfile
from ckanapi import LocalCKAN

import pytest
from ckanext.canada.tests.fixtures import prepare_dataset_type_with_resource

from ckanext.recombinant.tables import get_chromo, get_geno
from ckanext.recombinant.controller import _process_upload_file
from ckanext.recombinant.write_excel import excel_template, append_data
from ckanext.recombinant.errors import  BadExcelData
from openpyxl import load_workbook, Workbook


# testing the upload of PD template files
# 'wrongdoing' PD template is used as an example here
@pytest.mark.usefixtures('clean_db', 'prepare_dataset_type_with_resources')
@pytest.mark.parametrize(
    'prepare_dataset_type_with_resources',
    [{
        'dataset_type': 'wrongdoing',
        'cache_variables': ['org', 'pkg_id']
    }],
    indirect=True)
class TestXlsUpload(object):
    def test_upload_empty(self, request):
        lc = LocalCKAN()
        wb = excel_template('wrongdoing', request.config.cache.get("org", None))
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        wb.save(f.name)
        with pytest.raises(BadExcelData) as e:
            _process_upload_file(
                lc,
                lc.action.package_show(id=request.config.cache.get("pkg_id", None)),
                f.name,
                get_geno('wrongdoing'),
                True)
        assert e.value.message == 'The template uploaded is empty'


    def test_upload_example(self, request):
        lc = LocalCKAN()
        wb = excel_template('wrongdoing', request.config.cache.get("org", None))
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")

        # Enter the example record into the excel template
        record = get_chromo('wrongdoing')['examples']['record']
        wb = append_data(wb, [record], get_chromo('wrongdoing'))
        wb.save(f.name)

        _process_upload_file(
            lc,
            lc.action.package_show(id=request.config.cache.get("pkg_id", None)),
            f.name,
            get_geno('wrongdoing'),
            True)


    def test_upload_wrong_type(self, request):
        lc = LocalCKAN()
        wb = excel_template('travela', request.config.cache.get("org", None))
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        wb.save(f.name)
        with pytest.raises(BadExcelData) as e:
            _process_upload_file(
                lc,
                lc.action.package_show(id=request.config.cache.get("pkg_id", None)),
                f.name,
                get_geno('wrongdoing'),
                True)
        assert e.value.message == 'Invalid file for this data type. Sheet must be labeled "wrongdoing", but you supplied a sheet labeled "travela"'
