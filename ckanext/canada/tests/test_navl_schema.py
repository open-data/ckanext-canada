from ckan.tests import WsgiAppCase
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanapi import TestAppCKAN
import json

class TestNAVLSchema(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.sysadmin_action = TestAppCKAN(cls.app,
            str(cls.sysadmin_user.apikey)).action
        cls.action = TestAppCKAN(cls.app).action

    def test_basic_package(self, package_name=u'test_package', **kwargs):
        package = {
            'name': package_name,
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }
        package.update(kwargs)

        resp = self.sysadmin_action.package_create(**package)
        assert resp['result']['title'] == u'A Novel By Tolstoy'

        resp = self.action.package_show(id=resp['result']['id'])
        assert resp['result']['title'] == u'A Novel By Tolstoy'

