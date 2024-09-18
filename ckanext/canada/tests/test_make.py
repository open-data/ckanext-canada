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
    ckan_ini = request.config.getoption('--ckan-ini')
    if not ckan_ini.startswith('/'):
        ckan_ini = '{0}/{1}'.format(os.getcwd(), ckan_ini)
    setattr(request.cls, 'ckan_ini', ckan_ini)


@pytest.mark.usefixtures("set_ini_class_prop")
class TestMakePD(CanadaTestBase):
    """
    Test cases for nightly re-builds of PD types.

    These are extremely important test cases to ensure that PD records
    are re-built and published properly.

    # TODO: update Django search re-build test cases once we have a
    #       published Docker image of our search application.
    """
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestMakePD, self).setup_method(method)

        self.org = Organization(umd_number='example_umd',
                                department_number='example_department')

        self.action = LocalCKAN().action

        self.tmp_dir = mkdtemp()

        os.environ['TMPDIR'] = '/tmp'
        os.environ['PD_FILTER_SCRIPT_DIRECTORY'] = PD_FILTER_SCRIPT_DIRECTORY
        os.environ['REGISTRY_PASTER_COMMAND'] = 'paster'
        os.environ['REGISTRY_PYTHON_COMMAND'] = 'python3'
        os.environ['REGISTRY_CKANAPI_COMMAND'] = 'ckanapi'
        os.environ['OGC_SEARCH_COMMAND'] = 'echo'  # need a command to not fail
        os.environ['OC_SEARCH_COMMAND'] = 'echo'  # need a command to not fail
        os.environ['PD_BACKUP_DIRECTORY'] = self.tmp_dir
        os.environ['REGISTRY_STATIC_SMB_DIRECTORY'] = self.tmp_dir
        os.environ['PORTAL_STATIC_SMB_DIRECTORY'] = self.tmp_dir
        os.environ['REGISTRY_CKAN_COMMAND'] = 'ckan'


    @classmethod
    def teardown_method(self, method):
        """Method is called at class level after EACH test methods of the class are called.
        Remove any state specific to the execution of the given class methods.
        """
        shutil.rmtree(self.tmp_dir)


    def _setup_ini(self, ini):
        assert ini.startswith('/')
        os.environ['REGISTRY_INI'] = ini
        os.environ['PORTAL_INI'] = ini


    def _setup_pd(self, type, nil_type=None, extra_resource_ids=[]):
        assert type

        self.action.recombinant_create(dataset_type=type, owner_org=self.org['name'])

        rval = self.action.recombinant_show(dataset_type=type, owner_org=self.org['name'])

        chromo = get_chromo(type)

        self.action.datastore_upsert(
            resource_id=rval['resources'][0]['id'],
            records=[chromo['examples']['record']])

        if 'published_resource_id' in chromo:
            Resource(id=chromo['published_resource_id'])

        if nil_type:
            nil_chromo = get_chromo(nil_type)

            self.action.datastore_upsert(
                resource_id=rval['resources'][1]['id'],
                records=[nil_chromo['examples']['record']])

            if 'published_resource_id' in nil_chromo:
                Resource(id=nil_chromo['published_resource_id'])

        for _id in extra_resource_ids:
            Resource(id=_id)


    def test_enivonment_variables(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        make_process = subprocess.Popen(["make help"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

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
        assert 'REGISTRY_CKAN_COMMAND is undefined' not in stdout


    def test_make_ati(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='ati', nil_type='ati-nil')

        make_process = subprocess.Popen(["make upload-ati"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-ati] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-ati"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Drupal/Solr, test for record indexing
        assert "Usage:" not in stdout
        assert "rebuild-ati] Error" not in stdout
        assert '%s 1' % self.org['name'] in stdout


    def test_make_briefingt(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='briefingt', nil_type='briefingt-nil')

        make_process = subprocess.Popen(["make upload-briefingt"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-briefingt] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-briefingt"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-briefingt] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_qpnotes(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='qpnotes', nil_type='qpnotes-nil')

        make_process = subprocess.Popen(["make upload-qpnotes"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-qpnotes] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-qpnotes"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-qpnotes] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_contracts(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='contracts', nil_type='contracts-nil')

        make_process = subprocess.Popen(["make upload-contracts"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-contracts] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-contracts"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-contracts] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_contractsa(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='contractsa')

        make_process = subprocess.Popen(["make upload-contractsa"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-contractsa] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-contractsa"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # there is no search for contractsa, just test for no errors
        assert "Usage:" not in stdout
        assert "rebuild-contractsa] Error" not in stdout


    def test_make_consultations(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='consultations',
                       extra_resource_ids=['897d3008-b258-4a68-8c02-3e3c099a42c8',
                                           'aa606d25-4387-4bc6-89eb-12d66f5e9044',])

        make_process = subprocess.Popen(["make upload-consultations"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-consultations] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-consultations"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # there is no search for contractsa, just test for no errors
        assert "Usage:" not in stdout
        assert "rebuild-consultations] Error" not in stdout


    def test_make_dac(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='dac')

        make_process = subprocess.Popen(["make upload-dac"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-dac] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-dac"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # there is no search for contractsa, just test for no errors
        assert "Usage:" not in stdout
        assert "rebuild-dac] Error" not in stdout


    def test_make_experiment(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='experiment')

        make_process = subprocess.Popen(["make upload-experiment"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-experiment] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-experiment"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # there is no search for contractsa, just test for no errors
        assert "Usage:" not in stdout
        assert "rebuild-experiment] Error" not in stdout


    def test_make_grants(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='grants', nil_type='grants-nil')

        make_process = subprocess.Popen(["make upload-grants"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-grants] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-grants"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-grants] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_hospitalityq(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='hospitalityq', nil_type='hospitalityq-nil')

        make_process = subprocess.Popen(["make upload-hospitalityq"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-hospitalityq] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-hospitalityq"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Drupal/Solr, test for record indexing
        assert "Usage:" not in stdout
        assert "rebuild-hospitalityq] Error" not in stdout
        assert '%s 1' % self.org['name'] in stdout


    def test_make_travelq(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='travelq', nil_type='travelq-nil')

        make_process = subprocess.Popen(["make upload-travelq"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-travelq] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-travelq"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-travelq] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_nap5(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='nap5')

        make_process = subprocess.Popen(["make upload-nap5"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-nap5] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-nap5"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-nap5] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_reclassification(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='reclassification', nil_type='reclassification-nil')

        make_process = subprocess.Popen(["make upload-reclassification"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-reclassification] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-reclassification"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Drupal/Solr, test for record indexing
        assert "Usage:" not in stdout
        assert "rebuild-reclassification] Error" not in stdout
        assert '%s 1' % self.org['name'] in stdout


    def test_make_service(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='service', nil_type='service-std')

        make_process = subprocess.Popen(["make upload-service"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-service] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-service"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # there is no search for service inventory, just test for no errors
        assert "Usage:" not in stdout
        assert "rebuild-service] Error" not in stdout


    def test_make_travela(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='travela')

        make_process = subprocess.Popen(["make upload-travela"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-travela] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-travela"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-travela] Error" not in stdout
        assert 'import_data_csv' in stdout


    def test_make_wrongdoing(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='wrongdoing')

        make_process = subprocess.Popen(["make upload-wrongdoing"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-wrongdoing] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-wrongdoing"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Drupal/Solr, test for record indexing
        assert "Usage:" not in stdout
        assert "rebuild-wrongdoing] Error" not in stdout
        assert '%s 1' % self.org['name'] in stdout


    def test_make_adminaircraft(self):
        assert self.ckan_ini
        self._setup_ini(self.ckan_ini)

        self._setup_pd(type='adminaircraft')

        make_process = subprocess.Popen(["make upload-adminaircraft"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        assert "Usage:" not in stdout
        assert "upload-adminaircraft] Error" not in stdout

        make_process = subprocess.Popen(["make rebuild-adminaircraft"], shell=True, cwd=MAKE_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = make_process.communicate()

        stdout = stdout.decode("utf-8")

        # Django, just test for command output from echo
        assert "Usage:" not in stdout
        assert "rebuild-adminaircraft] Error" not in stdout
        assert 'import_data_csv' in stdout
