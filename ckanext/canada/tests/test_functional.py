import cgi
import datetime

from ckan import plugins
from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

import pytest


class TestNew(object):
    pkg_names = []

    def test_new_required_fields(self):
        pytest.skip('XXX: need to update for new forms')
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

        res = self.app.get(res.header('Location'),
            extra_environ=self.extra_environ_tester)
        fv = res.forms['dataset-form']
        fv['name'] = 'english resource name'
        fv['name_fra'] = 'french resource name'
        fv['resource_type'] = 'file'
        fv['url'] = 'somewhere'
        fv['format'] = 'TXT'
        fv['language'] = 'zxx; CAN'
        # Submit
        res = fv.submit('save', 2,
            extra_environ=self.extra_environ_tester)

        # Check resource page
        assert not 'Error' in res, res

    def test_new_missing_fields(self):
        pytest.skip('XXX: need to update for new forms')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Create dataset' in res
        fv = res.forms['dataset-form']
        fv['owner_org'] = '9391E0A2-9717-4755-B548-4499C21F917B' # nrcan
        # Submit
        res = fv.submit('save', extra_environ=self.extra_environ_tester)

        assert 'Error' in res, res
        assert 'Title French:Missing value' in res, res
        assert 'Subject:Missing value' in res, res
        assert 'Title English:Missing value' in res, res
        assert 'Description English:Missing value' in res, res
        assert 'Description French:Missing value' in res, res
        assert 'Tags English:Missing value' in res, res
        assert 'Tags French:Missing value' in res, res
        assert 'Date Published:Missing value' in res, res
        assert 'Frequency:Missing value' in res, res

        fv = res.forms['dataset-form']
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
        assert 'Error' not in res, res

        res = self.app.get(res.header('Location'),
            extra_environ=self.extra_environ_tester)
        fv = res.forms['dataset-form']
        fv['url'] = 'somewhere'
        # Submit
        res = fv.submit('save', 2,
            extra_environ=self.extra_environ_tester)

        assert 'Error' in res, res
        assert 'Title English:Missing value' in res, res
        assert 'Title French:Missing value' in res, res
        assert 'Format:Missing value' in res, res
        assert 'Language:Missing value' in res, res

        fv = res.forms['dataset-form']

        fv['name'] = 'english resource name'
        fv['name_fra'] = 'french resource name'
        fv['resource_type'] = 'file'
        fv['format'] = 'TXT'
        fv['language'] = 'zxx; CAN'
        # Submit
        res = fv.submit('save', 2,
            extra_environ=self.extra_environ_tester)

        # Check resource page
        assert not 'Error' in res, res
