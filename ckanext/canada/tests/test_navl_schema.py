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

    def test_basic_package(self):
        package = {
            'name': u'test_package',
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }

        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            **package)

        # fields we require
        package['catalog_type'] = u'Data | Données'
        package['title_fra'] = u'Un novel par Tolstoy'
        package['maintenance_and_update_frequency'] = u'As Needed | Au besoin'
        package['notes'] = u'...'
        package['notes_fra'] = u'...'
        package['keywords'] = u'book'
        package['keywords_fra'] = u'livre'

        resp = self.sysadmin_action.package_create(**package)
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['result']['id'])
        assert resp['result']['title_fra'] == u'Un novel par Tolstoy'

