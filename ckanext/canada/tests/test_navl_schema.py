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
        cls.sysadmin_action = TestAppCKAN(cls.app,
            str(cls.sysadmin_user.apikey)).action
        cls.action = TestAppCKAN(cls.app).action

        cls.incomplete_pkg = {
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }

        cls.complete_pkg = dict(cls.incomplete_pkg,
            catalog_type=u'Data | Données',
            title_fra=u'Un novel par Tolstoy',
            maintenance_and_update_frequency=u'As Needed | Au besoin',
            notes=u'...',
            notes_fra=u'...',
            keywords=u'book',
            keywords_fra=u'livre')

    def test_basic_package(self):
        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            name='basic_package', **self.incomplete_pkg)

        resp = self.sysadmin_action.package_create(
            name='basic_package', **self.complete_pkg)
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['result']['id'])
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'
