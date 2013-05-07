from ckan.tests import WsgiAppCase, CheckMethods
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanext.canada.commands import _trim_package

from ckanapi import TestAppCKAN, ValidationError
import json

class TestTrimPackage(WsgiAppCase, CheckMethods):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')

        cls.sysadmin_action = TestAppCKAN(cls.app,
            str(cls.sysadmin_user.apikey)).action

        cls.example_pkg = [
            json.loads(j) for j in EXAMPLE_JSON.strip().split('\n')]

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()

    def test_identify_unchanged(self):
        resp = self.sysadmin_action.package_create(
            **self.example_pkg[0])

        original = json.loads(json.dumps(self.example_pkg[0]))
        _trim_package(original)
        existing = resp['result']
        _trim_package(existing)
        self.assert_equal(
            _trim_package(self.example_pkg[0]),
            _trim_package(resp['result']))



EXAMPLE_JSON = r"""
{"validation_override": true, "portal_release_date": "", "data_series_issue_identification_fra": "", "catalog_type": "Data | Donn\u00e9es", "title_fra": "Enqu\u00eate du minist\u00e8re des Finances aupr\u00e8s du secteur priv\u00e9 - d\u00e9cembre 2009 (Version anglaise)", "keywords": "economic conditions, economic situation, fiscal planning, inflation, GDP, gross domestic product, CPI, consumer price index, employment growth, job growth, unemployment rate, T-bills, Treasury bills, government securities, economic forecasts, American economy, U.S. economy, United States economy, economic trends, price indexes, economic price indexes\n", "data_series_issue_identification": "", "ready_to_publish": "", "id": "dfba4540-8384-4dba-8632-4399696ff252", "subject": "Economics and Industry  \u00c9conomie et industrie", "data_series_name_fra": "", "spatial_representation_type": "", "maintenance_and_update_frequency": "Quarterly | Trimestriel", "title": "Department of Finance Private Sector Survey - December 2009 (English version)", "author_email": "open-ouvert@tbs-sct.gc.ca", "geographic_region": "", "notes_fra": "Donn\u00e9es de d\u00e9cembre 2009 de l'enqu\u00eate du minist\u00e8re des Finances aupr\u00e8s des pr\u00e9visionnistes \u00e9conomiques du secteur priv\u00e9. Donn\u00e9es pour les pr\u00e9visions de 2009 jusqu'en 2015.\n", "digital_object_identifier": "", "presentation_form": "", "spatial": "", "license_id": "", "resources": [{"url": "http://www.fin.gc.ca/pub/psf-psp/index-eng.asp", "language": "eng; CAN", "resource_type": "doc", "format": "HTML"}, {"url": " http://registry.data.gc.ca/commonwebsol/fileuploads/5/B/F/5BF2F561-84DE-4507-9676-4BC714EF3448/Data Dictionary - English.txt|Data Dictionary - English.txt", "language": "eng; CAN", "resource_type": "doc", "format": "HTML"}, {"url": "http://www.fin.gc.ca/pub/psf-psp/index-fra.asp", "language": "fra; CAN", "resource_type": "doc", "format": "HTML"}, {"url": " http://registry.data.gc.ca/commonwebsol/fileuploads/3/1/3/313B5F68-22A4-4745-85FD-4097E765E4BF/Dictionnaire de donn\u00e9es - Fran\u00e7ais.txt|Dictionnaire de donn\u00e9es - Fran\u00e7ais.txt", "language": "fra; CAN", "resource_type": "doc", "format": "HTML"}, {"url": "http://www.fin.gc.ca/pub/psf-psp/txt_eng/2009/Dec_2009.txt", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "CSV"}, {"url": "http://www.fin.gc.ca/pub/psf-psp/txt_fra/2009/Sep_2009.txt", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "CSV"}], "browse_graphic_url": "", "topic_category": "", "endpoint_url_fra": "", "date_published": "2010-09-14", "time_period_coverage_start": "2009-01-01", "data_series_name": "", "url_fra": "http://www.fin.gc.ca/branches-directions/efp-fra.asp", "endpoint_url": "", "time_period_coverage_end": "2009-01-01", "language": "", "date_modified": "2010-09-14", "url": "http://www.fin.gc.ca/branches-directions/efp-eng.asp", "notes": "December 2009 data from the Department of Finance survey of private sector economic forecasters. Data for forecasts from 2009 to 2015.\n", "owner_org": "05D03DCB-5906-4555-A5A1-84D86E9E94DD", "keywords_fra": "conditions \u00e9conomiques, situation \u00e9conomique, planification financi\u00e8re, inflation, PIB, produit int\u00e9rieur brut, IPC, indice des prix \u00e0 la consommation, croissance de l-emploi, taux de ch\u00f4mage, bon du Tr\u00e9sor, titre d-\u00c9tat, \u00e9conomie am\u00e9ricaine, \u00e9conomie des \u00c9tats-Unis, \u00e9conomie des \u00c9.-U., tendances \u00e9conomiques, indice des prix\n", "resource_type": "file"}
"""
