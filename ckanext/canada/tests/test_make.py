# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase

import os
import subprocess
import pytest
import shutil
import logging
from tempfile import mkdtemp
from ckan import plugins
from ckan.lib.uploader import get_resource_uploader
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaResource as Resource,
)

from ckanapi import LocalCKAN

from ckanext.recombinant.tables import get_chromo
from ckanext.xloader import loader

logger = logging.getLogger(__name__)


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

        if not plugins.plugin_loaded('xloader'):
            plugins.load('xloader')

        if plugins.plugin_loaded('validation'):
            plugins.unload('validation')

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
        if plugins.plugin_loaded('xloader'):
            plugins.unload('xloader')

        if not plugins.plugin_loaded('validation'):
            plugins.load('validation')

        shutil.rmtree(self.tmp_dir)


    def _get_ds_records(self, type):
        chromo = get_chromo(type)
        result = self.action.datastore_search(resource_id=chromo['published_resource_id'])
        return result.get('fields'), result.get('records')


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

        # test the published service resource
        chromo = get_chromo('service')
        resource_filepath = get_resource_uploader(self.action.resource_show(id=chromo['published_resource_id'])).get_path(chromo['published_resource_id'])

        loader.load_csv(
            resource_filepath,
            resource_id=chromo['published_resource_id'],
            mimetype="text/csv",
            logger=logger,
        )

        published_fields, published_records = self._get_ds_records('service')
        published_record = published_records[0]

        expected_fields = ['_id']
        removed_fields = ['record_created', 'record_modified', 'user_modified']
        for field in chromo['fields']:
            if field['datastore_id'] in removed_fields:
                continue
            expected_fields.append(field['datastore_id'])

        published_fields = [f['id'] for f in published_fields]

        expected_record = {
            '_id': published_record['_id'],
            'fiscal_yr': '2022-2023',
            'service_id': '1001',
            'service_name_en': 'Old Age Security (OAS) Benefits',
            'service_name_fr': 'Prestations de la Sécurité de la vieillesse',
            'service_description_en': 'The Old Age Security (OAS) pension is a monthly payment available to most Canadians 65 years of age who meet the Canadian legal status and residence requirements. In addition to the Old Age Security pension, there are three types of Old Age Security benefits:  the Guaranteed Income Supplement, Allowance and Allowance for the Survivor. The OAS provides financial support to millions of seniors, including those that are low-income, each year.',
            'service_description_fr': "La pension de la Sécurité de la vieillesse (SV) est une prestation mensuelle versée à la plupart des Canadiens âgés de 65 ans et plus qui satisfont aux exigences relatives au statut juridique et à la résidence au Canada. En plus de la pension de la Sécurité de la vieillesse, il existe trois types de prestations de la Sécurité de la vieillesse : le Supplément de revenu garanti, l'Allocation et l'Allocation au survivant. La SV verse chaque année un soutien financier à des millions d'aînés, incluant ceux à faible revenu.",
            'service_type': 'RES',
            'service_recipient_type': 'CLIENT',
            'service_scope': 'EXTERN',
            'client_target_groups': 'PERSON',
            'program_id': 'BGN01',
            'program_name_en': "'Old Age Security'",
            'program_name_fr': "'Sécurité de la vieillesse'",
            'client_feedback_channel': 'EML,FAX,ONL,PERSON,POST,TEL',
            'automated_decision_system': 'N',
            'automated_decision_system_description_en': None,
            'automated_decision_system_description_fr': None,
            'service_fee': 'N',
            'os_account_registration': 'Y',
            'os_authentication': 'Y',
            'os_application': 'Y',
            'os_decision': 'Y',
            'os_issuance': 'Y',
            'os_issue_resolution_feedback': 'Y',
            'os_comments_client_interaction_en': None,
            'os_comments_client_interaction_fr': None,
            'last_service_review': None,
            'last_service_improvement': '2021-2022',
            'sin_usage': 'Y',
            'cra_bn_identifier_usage': 'Y',
            'num_phone_enquiries': '7252346',
            'num_applications_by_phone': '0',
            'num_website_visits': '5446484',
            'num_applications_online': '276390',
            'num_applications_in_person': '0',
            'num_applications_by_mail': '792026',
            'num_applications_by_email': '0',
            'num_applications_by_fax': '0',
            'num_applications_by_other': '2218002',
            'num_applications_total': '3286418',
            'special_remarks_en': "- The volume reflected in the 'Applications by Mail' column include the volume of paper applications for the following OAS pension benefits application types: OAS basic pension; the Guaranteed Income Supplement (GIS); Allowance; Allowance Survivor; Renewal of GIS/Allowance/Allowance Survivor; Options for GIS/Allowance/Allowance Survivor; and foreign benefits.\n- The volume reflected in the 'Number of Automatic Enrolments' column represents the volume of Automatic Enrolment into the OAS basic pension and the GIS.\n- The volume reflected in the 'Applications through Other Channels' column represents the volume of the Automatic Renewal of income-tested benefits through the CRA for the GIS.\n- Applications to OAS pension benefits do not constitute the largest volume of work done by the OAS program. In addition to applications, there were also another 3,143,898 OAS and foreign benefit account revisions in 2022-2023.\n- OAS and CPP telephone enquiries are managed through the same Pensions Toll-free service, with significant overlap between the two programs on many calls. The metrics reported for CPP and OAS,  such as the volume of calls, are therefore identical and are non-cumulative (i.e. they are not to be added together).\"",
            'special_remarks_fr': "- Le volume indiqué dans la colonne « Demandes par la poste » comprend le volume de demandes papier pour les types de demandes de prestations de pension de la SV suivants : pension de base de la SV ; le Supplément de revenu garanti (SRG); Allocation ; Allocation de survivant ; Renouvellement du SRG/Allocation/ Allocation de survivant ; options pour le SRG/l'allocation/l'allocation de survivant ; et les prestations étrangères.\n- Le volume indiqué dans la colonne \"\"Nombre d'inscriptions automatiques\"\" représente le volume des inscriptions automatiques à la pension de base de la SV et au SRG.\n- Le volume reflété dans la colonne « Demandes par d'autres canaux » représente le volume d'adhésion automatique à la pension de base de la SV et du SRG, ainsi que le renouvellement automatique des prestations fondées sur le revenu par l'intermédiaire de l'ARC pour le SRG.\n- Les demandes de prestations de pension de la SV ne constituent pas le plus gros volume de travail effectué par le programme de la SV. En plus des demandes, il y a eu également 3 143 898 autres révisions des comptes de SV et de prestations étrangères en 2022-2023\n- Les demandes de renseignements téléphoniques sur la SV et le RPC sont gérées par le même service téléphonique sans frais des pensions, avec un chevauchement important entre les deux programmes pour de nombreux appels. Les mesures rapportées pour le RPC et la SV, comme le volume d'appels, sont donc identiques et non cumulatives (c'est-à-dire qu'elles ne doivent pas être additionnées). \"",
            'service_uri_en': 'https://www.canada.ca/en/services/benefits/publicpensions/cpp/old-age-security.html',
            'service_uri_fr': 'https://www.canada.ca/fr/services/prestations/pensionspubliques/rpc/securite-vieillesse.html',
            'owner_org': self.org['name'],
            'owner_org_title': self.org['title'],
        }

        assert expected_fields == published_fields
        assert expected_record == published_record

        # test the published service-std resource
        chromo = get_chromo('service-std')
        resource_filepath = get_resource_uploader(self.action.resource_show(id=chromo['published_resource_id'])).get_path(chromo['published_resource_id'])

        loader.load_csv(
            resource_filepath,
            resource_id=chromo['published_resource_id'],
            mimetype="text/csv",
            logger=logger,
        )

        published_fields, published_records = self._get_ds_records('service-std')
        published_record = published_records[0]

        expected_fields = ['_id']
        removed_fields = ['record_created', 'record_modified', 'user_modified']
        for field in chromo['fields']:
            if field['datastore_id'] in removed_fields:
                continue
            expected_fields.append(field['datastore_id'])

        published_fields = [f['id'] for f in published_fields]

        expected_record = {
            '_id': published_record['_id'],
            'fiscal_yr': '2022-2023',
            'service_id': '1001',
            'service_name_en': 'Old Age Security (OAS) Benefits',
            'service_name_fr': 'Prestations de la Sécurité de la vieillesse',
            'service_standard_id': '925',
            'service_standard_en': 'OAS basic benefits are paid within the first month of entitlement',
            'service_standard_fr': 'Les prestations de base de la SV sont versées au cours du premier mois d’admissibilité.',
            'type': 'TML',
            'channel': 'OTH',
            'channel_comments_en': 'Mail, Online, Person',
            'channel_comments_fr': 'Courrier, en ligne, personne',
            'target': '0.9',
            'volume_meeting_target': '315128',
            'total_volume': '359919',
            'performance': '0.8756',
            'comments_en': 'The total volumes assessed against the first month of entitlement service standard excludes 3,550 decisions involving files submitted under international agreements and interactions with foreign governments.',
            'comments_fr': "Les volumes totaux évalués par rapport à la norme de service du premier mois de droit excluent 3 550 décisions concernant des dossiers soumis dans le cadre d'accords internationaux et d'interactions avec des gouvernements étrangers.",
            'target_met': 'N',
            'standards_targets_uri_en': 'https://www.canada.ca/en/employment-social-development/corporate/transparency/service-standards-2018-2019.html#h2.25',
            'standards_targets_uri_fr': 'https://www.canada.ca/fr/emploi-developpement-social/ministere/transparence/normes-service-2018-2019.html#h2.21',
            'performance_results_uri_en': 'Not applicable',
            'performance_results_uri_fr': 'Not applicable',
            'owner_org': self.org['name'],
            'owner_org_title': self.org['title'],
        }

        assert expected_fields == published_fields
        assert expected_record == published_record


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
