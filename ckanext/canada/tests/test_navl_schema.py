# -*- coding: UTF-8 -*-
from ckan.tests import WsgiAppCase, CheckMethods
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanapi import TestAppCKAN, ValidationError
import json

NRCAN_UUID = '9391E0A2-9717-4755-B548-4499C21F917B'

class TestNAVLSchema(WsgiAppCase, CheckMethods):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')

        cls.sysadmin_action = TestAppCKAN(cls.app,
            str(cls.sysadmin_user.apikey)).action
        cls.normal_action = TestAppCKAN(cls.app,
            str(cls.normal_user.apikey)).action
        cls.action = TestAppCKAN(cls.app).action

        cls.sysadmin_action.organization_member_create(
            username='annafan', id=NRCAN_UUID, role='editor')

        cls.incomplete_pkg = {
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'TXT',
                'url': u'http://www.annakarenina.com/download/',
                'resource_type': 'file',
                'language': 'zxx; CAN',
            }],
        }

        cls.override_possible_pkg = dict(cls.incomplete_pkg,
            owner_org=NRCAN_UUID)

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

    def test_validation_override(self):
        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            **self.incomplete_pkg)

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            validation_override=True, **self.override_possible_pkg)

        self.sysadmin_action.package_create(
            validation_override=True, **self.override_possible_pkg)

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

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **geo_pkg)

        geo_pkg['topic_category'] = [u"Society  Société",
            u"Structure  Structures"]

        self.normal_action.package_create(**geo_pkg)

    def test_pilot_uuids(self):
        pilot_pkg = dict(self.complete_pkg,
            subject=['BEF4D60C-E2D1-46B9-96C0-B55902F076F1'],
            )

        pkg = self.normal_action.package_create(**pilot_pkg)
        assert pkg['subject'] == [u"Persons  Personnes"]

        resp = self.action.package_show(id=pkg['id'])
        assert resp['result']['subject'] == [u"Persons  Personnes"]

