from ckan.tests.legacy import WsgiAppCase, CheckMethods
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanapi import TestAppCKAN, ValidationError
import json
from nose.plugins.skip import SkipTest

class TestTrimPackage(WsgiAppCase, CheckMethods):

    @classmethod
    def setup_class(cls):
        cls.example_pkg = [
            json.loads(j) for j in EXAMPLE_JSON_LINES.strip().split('\n')]


    def test_identify_unchanged(self):
        #TODO: bring in this test
        raise SkipTest('XXX: trim package needs to be updated for our new schemas')
        for p in self.example_pkg:
            resp = self.sysadmin_action.package_create(**p)

            self._trim_compare(p, resp)

    def _trim_compare(self, original, existing):
        "make a copy of original so that it is not modified"
        original = json.loads(json.dumps(original))
        _trim_package(original)
        _trim_package(existing)
        self.assert_equal(set(original) - set(existing), set([]))
        self.assert_equal(set(existing) - set(original), set([]))
        for k in original:
            if k == 'resources':
                continue
            self.assert_equal((k, original[k]), (k, existing[k]))
        self.assert_equal(len(original['resources']),
            len(existing['resources']))
        for n, res in enumerate(original['resources']):
            self.assert_equal(('resources', n, res),
                ('resources', n, existing['resources'][n]))


EXAMPLE_JSON_LINES = r"""
{"ready_to_publish": false, "catalog_type": "Data | Donn\u00e9es", "title_fra": "Indicateurs des \u00e9missions de gaz \u00e0 effet de serre - \u00c9missions de gaz \u00e0 effet de serre par installation d'envergure, Canada, 2010", "keywords": "environmental indicators, air and climate, greenhouse gas emissions, climate, greenhouse gases, carbon dioxide, carbon dioxide equivalent, large facilities", "id": "28e6fbf5-f9ff-4b77-8f71-c66f5b58926b", "subject": "Nature and Environment  Nature et environnement", "spatial_representation_type": "", "maintenance_and_update_frequency": "Unknown | Inconnu", "title": "Greenhouse Gas Emissions Indicators - Greenhouse gas emissions from large facilities, Canada, 2010", "author_email": "open-ouvert@tbs-sct.gc.ca", "geographic_region": "", "notes_fra": "Le programme des Indicateurs canadiens de la durabilit\u00e9 de l'environnement (ICDE) rend compte de la performance du Canada \u00e0 l'\u00e9gard d'enjeux cl\u00e9s en mati\u00e8re de d\u00e9veloppement durable. L'indicateur des \u00e9missions de gaz \u00e0 effet de serre des installations d'envergure est utilis\u00e9 pour suivre l'\u00e9volution des efforts d\u00e9ploy\u00e9s par le Canada afin de faire baisser les \u00e9missions et d'atteindre les objectifs de performance environnementale. On y utilise des r\u00e9partitions par secteur et par r\u00e9gion g\u00e9ographique pour faciliter l'\u00e9laboration de politiques et de plans de r\u00e9duction des \u00e9missions. Toutes les installations qui \u00e9mettent l'\u00e9quivalent de 50 000 tonnes (50 kt) ou plus de GES (en \u00e9quivalents de dioxyde de carbone [\u00e9q. CO2]) par an doivent pr\u00e9senter un rapport \u00e0 Environnement Canada. La d\u00e9claration obligatoire des \u00e9missions par les installations donnera un tableau plus pr\u00e9cis des sources et quantit\u00e9s des \u00e9missions de GES au Canada, ce qui permettra d'\u00e9laborer, mettre en ouvre et \u00e9valuer les politiques et strat\u00e9gies du Canada en mati\u00e8re de changement climatique et d'\u00e9nergie. Cette information est rendue disponible aux Canadiens sous plusieurs formats: cartes statiques et interactives, figures et graphiques, tableaux de donn\u00e9es HTML et CSV et rapports t\u00e9l\u00e9chargeables. Voir l'autre documentation pour les sources des donn\u00e9es et pour lire comment les donn\u00e9es sont collect\u00e9es et comment l'indicateur est calcul\u00e9.", "presentation_form": "", "spatial": "", "license_id": "ca-ogl-lgo", "resources": [{"name": "a", "name_fra": "b", "url": "http://www.ec.gc.ca/indicateurs-indicators/default.asp?lang=En&n=130FFF78-1", "language": "eng; CAN", "resource_type": "doc", "format": "HTML"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/default.aspx?mapId=1&xMin=-17200268.28492363&yMin=4842529.641591634&xMax=-5498653.153107968&yMax=12669696.953842915&lang=en, http://www.ec.gc.ca/indicateurs-indicators/default.asp?lang=en&n=3F4A5494-1", "language": "eng; CAN", "resource_type": "doc", "format": "HTML"}, {"name": "a", "name_fra": "b", "url": "http://www.ec.gc.ca/indicateurs-indicators/default.asp?lang=fr&n=130FFF78-1", "language": "fra; CAN", "resource_type": "doc", "format": "HTML"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/default.aspx?mapId=1&xMin=-17200268.28492363&yMin=4842529.641591634&xMax=-5498653.153107968&yMax=12669696.953842915&lang=fr, http://www.ec.gc.ca/indicateurs-indicators/default.asp?lang=fr&n=3F4A5494-1", "language": "fra; CAN", "resource_type": "doc", "format": "HTML"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/TableView.aspx?ID=1&lang=en", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "CSV"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/TableView.aspx?ID=1&lang=fr", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "CSV"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/kmz/CESI_GHG_n.kmz", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "kml / kmz"}, {"name": "a", "name_fra": "b", "url": "http://maps-cartes.ec.gc.ca/indicators-indicateurs/kmz/ICDE_GES_n.kmz", "language": "eng; CAN | fra; CAN", "resource_type": "file", "format": "kml / kmz"}], "browse_graphic_url": "", "topic_category": "", "date_published": "2012-04-11", "time_period_coverage_start": "1000-01-01", "time_period_coverage_end": "3000-01-01", "language": "Bilingual (English and French) | Bilingue (Anglais et Fran\u00e7ais)", "date_modified": "", "notes": "The Canadian Environmental Sustainability Indicators (CESI) program provides data and information to track Canada's performance on key environmental sustainability issues. The greenhouse gas emissions from large facitities indicator is used to track the progress of Canada's efforts to lower emissions and reach environmental performance objectives. Sector and geographic breakdowns are used to inform policy development and emissions reduction plans. All facilities that emit the equivalent of 50 000 tonnes (50 kt) or more of GHGs (in carbon dioxide equivalent [CO2 eq] units) per year are required to submit a report to Environment Canada. Mandatory reporting of facility emissions will provide a more precise picture of the sources and amounts of Canada's GHG emissions, thus contributing to the development, implementation and evaluation of climate change and energy policies and strategies in Canada. Information is provided to Canadians in a number of formats including: static and interactive maps, charts and graphs, HTML and CSV data tables and downloadable reports. See supplementary documentation for data sources and details on how those data were collected and how the indicator was calculated.", "owner_org": "49E2ADF4-AD7A-43EB-85C8-6433D37ED62C", "keywords_fra": "indicateurs environnementaux, indicateur environnemental, air et climat, \u00e9missions de gaz \u00e0 effet de serre, climat, gaz \u00e0 effet de serre, dioxyde de carbone, en \u00e9quivalent de dioxyde de carbone, installations d'envergure", "resource_type": "file"}
{"ready_to_publish": false, "catalog_type": "Data | Donn\u00e9es", "title_fra": "Indicateurs de la qualit\u00e9 de l'eau - La qualit\u00e9 de l'eau douce aux stations de suivi  de 2007 \u00e0 2009, au Canada", "keywords": "aaa", "id": "00826755-9718-4285-a1d5-97cfba42626c", "subject": "Nature and Environment  Nature et environnement", "spatial_representation_type": "", "maintenance_and_update_frequency": "Unknown | Inconnu", "title": "Water Quality Indicators - Freshwater quality at monitoring stations for the 2007 to 2009 period, Canada", "author_email": "open-ouvert@tbs-sct.gc.ca", "geographic_region": "", "notes_fra": "b", "presentation_form": "", "spatial": "", "license_id": "ca-ogl-lgo", "resources": [], "browse_graphic_url": "", "topic_category": "", "date_published": "2012-04-05", "time_period_coverage_start": "1000-01-01", "time_period_coverage_end": "3000-01-01", "language": "Bilingual (English and French) | Bilingue (Anglais et Fran\u00e7ais)", "date_modified": "", "notes": "b", "owner_org": "49E2ADF4-AD7A-43EB-85C8-6433D37ED62C", "keywords_fra": "aaa", "resource_type": "file"}
"""
