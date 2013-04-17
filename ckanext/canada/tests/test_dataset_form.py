from ckan.tests import WsgiAppCase
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

import json

class TestDatasetForm(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')

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

        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert json.loads(res.body)['result']['title'] == u'A Novel By Tolstoy'
