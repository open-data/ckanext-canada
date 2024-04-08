# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase

import os
import subprocess
import pytest
import shutil
from tempfile import mkdtemp
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaResource as Resource,
)

from ckanapi import LocalCKAN

from ckanext.recombinant.tables import get_chromo


MAKE_PATH = path = '{0}/{1}'.format(os.path.dirname(os.path.realpath(__file__)), '../../../bin/pd')
PD_FILTER_SCRIPT_DIRECTORY = '{0}/{1}'.format(os.path.dirname(os.path.realpath(__file__)), '../../../bin/filter')


@pytest.fixture()
def set_ini_class_prop(request):
    #TODO: get abspath of the --ckan-ini
    setattr(request.cls, 'ckan_ini', request.config.getoption('--ckan-ini'))


@pytest.mark.usefixtures("set_ini_class_prop")
class TestMakePD(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestMakePD, self).setup_method(method)

        self.org = Organization()

        self.action = LocalCKAN().action

        self.tmp_dir = mkdtemp()

        os.environ['PD_FILTER_SCRIPT_DIRECTORY'] = PD_FILTER_SCRIPT_DIRECTORY
        os.environ['REGISTRY_PASTER_COMMAND'] = 'paster'
        os.environ['REGISTRY_PYTHON_COMMAND'] = 'python'
        os.environ['REGISTRY_CKANAPI_COMMAND'] = 'ckanapi'
        os.environ['OGC_SEARCH_COMMAND'] = 'echo'  # need a command to not fail
        os.environ['OC_SEARCH_COMMAND'] = 'echo'  # need a command to not fail
        os.environ['PD_BACKUP_DIRECTORY'] = self.tmp_dir
        os.environ['REGISTRY_STATIC_SMB_DIRECTORY'] = self.tmp_dir
        os.environ['PORTAL_STATIC_SMB_DIRECTORY'] = self.tmp_dir


    @classmethod
    def teardown_method(self, method):
        """Method is called at class level after EACH test methods of the class are called.
        Remove any state specific to the execution of the given class methods.
        """
        shutil.rmtree(self.tmp_dir)


    def _setup_ini(self, ini):
        os.environ['REGISTRY_INI'] = ini
        os.environ['PORTAL_INI'] = ini


    def _setup_pd(self, type, nil_type):
        assert type

        self.action.recombinant_create(dataset_type=type, owner_org=self.org['name'])

        rval = self.action.recombinant_show(dataset_type='ati', owner_org=self.org['name'])

        self.action.datastore_upsert(
            resource_id=rval['resources'][0]['id'],
            records=[get_chromo(type)['examples']['record']])

        Resource(id=rval['resources'][0]['published_resource_id'])

        if nil_type:
            self.action.datastore_upsert(
                resource_id=rval['resources'][1]['id'],
                records=[get_chromo(nil_type)['examples']['record']])

            Resource(id=rval['resources'][1]['published_resource_id'])


    def test_enivonment_variables(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        make_process = subprocess.Popen(["make help"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        assert 'PD_FILTER_SCRIPT_DIRECTORY is undefined' not in stdout
        assert 'REGISTRY_PASTER_COMMAND is undefined' not in stdout
        assert 'REGISTRY_PYTHON_COMMAND is undefined' not in stdout
        assert 'REGISTRY_INI is undefined' not in stdout
        assert 'PORTAL_INI is undefined' not in stdout
        assert 'REGISTRY_CKANAPI_COMMAND is undefined' not in stdout
        assert 'OGC_SEARCH_COMMAND is undefined' not in stdout
        assert 'OC_SEARCH_COMMAND is undefined' not in stdout
        assert 'PD_BACKUP_DIRECTORY is undefined' not in stdout
        assert 'REGISTRY_STATIC_SMB_DIRECTORY is undefined' not in stdout
        assert 'PORTAL_STATIC_SMB_DIRECTORY is undefined' not in stdout


    def test_make_ati(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='ati', nil_type='ati-nil')

        make_process = subprocess.Popen(["make upload-ati"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        #TODO: assert any failures
