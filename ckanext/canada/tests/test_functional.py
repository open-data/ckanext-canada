import cgi
import datetime

from genshi.core import escape as genshi_escape
from nose.tools import assert_equal

from ckan import plugins
from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

from ckan.tests.functional.test_package import TestPackageBase
from ckan.tests import WsgiAppCase

class TestNew(TestPackageBase):
    pkg_names = []

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.extra_environ_tester = {'REMOTE_USER': 'testsysadmin'}
        cls.sysadmin_user = model.User.get('testsysadmin')
        assert cls.sysadmin_user

    @classmethod
    def teardown_class(cls):
        cls.purge_packages(cls.pkg_names)
        CreateTestData.delete()

    def test_new_required_fields(self):
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Create dataset' in res
        fv = res.forms['dataset-form']
        fv['owner_org'] = '9391E0A2-9717-4755-B548-4499C21F917B' # nrcan
        fv['title'] = 'english title'
        fv['title_fra'] = 'french title'
        fv['notes'] = 'english description'
        fv['notes_fra'] = 'french description'
        fv.set('subject', True, index=1)
        fv['keywords'] = 'english keywords'
        fv['keywords_fra'] = 'french keywords'
        fv['date_published'] = '2000-01-01'
        fv['maintenance_and_update_frequency'] = 'As Needed | Au besoin'
        # Submit
        res = fv.submit('save', extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'Error' in res, res
