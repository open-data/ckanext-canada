# -*- coding: UTF-8 -*-
from ckan.tests import WsgiAppCase, CheckMethods
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanapi import TestAppCKAN, ValidationError
import json

class TestNAVLSchema(WsgiAppCase, CheckMethods):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.publisher_user = model.User.get('russianfan')

        cls.sysadmin_action = TestAppCKAN(cls.app,
            str(cls.sysadmin_user.apikey)).action
        cls.normal_action = TestAppCKAN(cls.app,
            str(cls.normal_user.apikey)).action
        cls.publisher_action = TestAppCKAN(cls.app,
            str(cls.publisher_user.apikey)).action
        cls.action = TestAppCKAN(cls.app).action

        cls.sysadmin_action.organization_member_create(
            username='annafan', id='nrcan-rncan', role='editor')

        cls.sysadmin_action.organization_member_create(
            username='russianfan', id='tb-ct', role='editor')

        cls.incomplete_pkg = {
            'title': u'A Novel By Tolstoy',
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': True,
            'resources': [{
                'name': u'Full text.',
                'name_fra': u'Full text.',
                'format': u'TXT',
                'url': u'http://www.annakarenina.com/download/',
                'size': 42,
                'resource_type': 'file',
                'language': 'zxx; CAN',
            }],
        }

        cls.override_possible_pkg = dict(cls.incomplete_pkg,
            owner_org='nrcan-rncan')

        cls.complete_pkg = dict(cls.override_possible_pkg,
            catalog_type=u'Data | Données',
            title_fra=u'Un novel par Tolstoy',
            maintenance_and_update_frequency=u'As Needed | Au besoin',
            notes=u'...',
            notes_fra=u'...',
            subject=[u'Persons  Personnes'],
            date_published=u'2013-01-01',
            keywords=u'book',
            keywords_fra=u'livre')

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()

    def test_basic_package(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='basic_package', **self.incomplete_pkg)

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='basic_package', **self.override_possible_pkg)

        resp = self.normal_action.package_create(
            name='basic_package', **self.complete_pkg)
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['result']['id'])
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'

    def test_keyword_validation(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg, keywords='not! ok!'))

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg, keywords_fra='one too short, q'))

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg, keywords='this is much too long' * 50))

        self.normal_action.package_create(
            name='keyword_validation',
            **dict(self.complete_pkg, keywords='these, ones, are, a-ok'))

    def test_custom_dataset_id(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='custom_dataset_id', id='my-custom-id', **self.complete_pkg)

        self.sysadmin_action.package_create(
            name='custom_dataset_id', id='my-custom-id', **self.complete_pkg)

        resp = self.action.package_show(id='my-custom-id')
        assert resp['result']['id'] == 'my-custom-id'
        assert resp['result']['name'] == 'custom_dataset_id'

        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            name='different_dataset_id', id='my-custom-id', **self.complete_pkg)

    def test_not_ready_to_publish(self):
        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            **self.incomplete_pkg)

        self.normal_action.package_create(
            **dict(self.override_possible_pkg, ready_to_publish=False))

    def test_raw_required(self):
        raw_pkg = dict(self.complete_pkg)
        del raw_pkg['subject']

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **raw_pkg)

    def test_geo_required(self):
        geo_pkg = dict(self.complete_pkg,
            catalog_type=u"Geo Data | Géo")

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **geo_pkg)

        geo_pkg.update({
            'spatial_representation_type': "Vector | Vecteur",
            'presentation_form': "Diagram Hardcopy | Diagramme papier",
            'browse_graphic_url': "http://example.com/example.jpg",
            })

        self.normal_action.package_create(**geo_pkg)

    def test_pilot_uuids(self):
        pilot_pkg = dict(self.complete_pkg,
            subject=['BEF4D60C-E2D1-46B9-96C0-B55902F076F1'],
            geographic_region=['E65D06CB-F120-43E6-B037-83F699C84BAE'],
            resources = [dict(self.complete_pkg['resources'][0],
                format='D91DAAF4-0BD5-4F0C-A4FA-F99E89642315',
                )],
            )

        resp = self.normal_action.package_create(**pilot_pkg)
        pkg = resp['result']
        assert pkg['subject'] == [u"Persons  Personnes"]
        assert pkg['geographic_region'] == [
            u"Newfoundland and Labrador  Terre-Neuve-et-Labrador"]
        assert pkg['resources'][0]['format'] == u'XML'

        resp = self.action.package_show(id=pkg['id'])
        pkg = resp['result']
        assert pkg['subject'] == [u"Persons  Personnes"]
        assert pkg['geographic_region'] == [
            u"Newfoundland and Labrador  Terre-Neuve-et-Labrador"]
        assert pkg['resources'][0]['format'] == u'XML'


    def test_tag_extras_bug(self):
        resp = self.normal_action.package_create(
            **self.complete_pkg)

        resp = self.action.package_show(id=resp['result']['id'])
        assert 'subject' not in [e['key'] for e in resp['result'].get('extras',[])]

    def test_keywords_with_apostrophe(self):
        self.normal_action.package_create(
            **dict(self.complete_pkg, keywords="emissions de l'automobile"))

    def test_treat_empty_string_as_no_tags(self):
        self.normal_action.package_create(
            **dict(self.complete_pkg, topic_category=''))

    def test_invalid_resource_size(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **dict(self.complete_pkg,
                resources = [dict(self.complete_pkg['resources'][0],
                    size='10M',
                    )],
                )
            )

    def test_generated_fields(self):
        resp = self.normal_action.package_create(**self.complete_pkg)

        pkg = resp['result']
        # not generated, we set this one but later tests depend on it
        self.assert_equal(pkg['license_id'], 'ca-ogl-lgo')
        # this one is generated in the bowels of CKAN's model_dictize
        self.assert_equal(pkg['license_title'],
            'Open Government Licence - Canada')
        # some we actually generate ourselves
        self.assert_equal(pkg['license_title_fra'],
            'Licence du gouvernement ouvert - Canada')
        assert pkg['license_url_fra']

        assert pkg['department_number']

    def test_portal_release_date(self):
        release_pkg = dict(self.complete_pkg,
            portal_release_date='2012-01-01',
            owner_org='tb-ct')

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **release_pkg)

        self.publisher_action.package_create(**release_pkg)

        self.sysadmin_action.package_create(**release_pkg)

    def test_publisher_authorities(self):
        "The publishing org (tb-ct by default) gets special authorities"
        # create packages belonging to other orgs
        self.publisher_action.package_create(**self.complete_pkg)

    def test_spatial(self):
        spatial_pkg = dict(self.complete_pkg,
            spatial='{"type": "Polygon", "coordinates": '
                '[[[-141.001333, 41.736231], [-141.001333, 82.514468], '
                '[-52.622540, 82.514468], [-52.622540, 41.736231], '
                '[-141.001333, 41.736231]]]}')
        self.normal_action.package_create(**spatial_pkg)

        bad_spatial_pkg = dict(self.complete_pkg,
            spatial='{"type": "Line", "coordinates": '
                '[[[-141.001333, 41.736231], [-141.001333, 82.514468], '
                '[-52.622540, 82.514468], [-52.622540, 41.736231], '
                '[-141.001333, 41.736231]]]}')
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg)

        bad_spatial_pkg2 = dict(self.complete_pkg,
            spatial='forty')
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg2)
