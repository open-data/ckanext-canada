# -*- coding: UTF-8 -*-
from ckan.tests import WsgiAppCase, CheckMethods
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

from ckanapi import TestAppCKAN, ValidationError
import json
from nose.plugins.skip import SkipTest

class TestNAVLSchema(WsgiAppCase, CheckMethods):

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.publisher_user = model.User.get('russianfan')

        cls.sysadmin_action = TestAppCKAN(cls.app,
            cls.sysadmin_user.apikey).action
        cls.normal_action = TestAppCKAN(cls.app,
            cls.normal_user.apikey).action
        cls.publisher_action = TestAppCKAN(cls.app,
            cls.publisher_user.apikey).action
        cls.action = TestAppCKAN(cls.app).action

        cls.sysadmin_action.organization_member_create(
            username='annafan', id='nrcan-rncan', role='editor')

        cls.sysadmin_action.organization_member_create(
            username='russianfan', id='tb-ct', role='editor')
        cls.sysadmin_action.organization_member_create(
            username='russianfan', id='nrcan-rncan', role='editor')

        cls.incomplete_pkg = {
            'type': 'dataset',
            'title': {'en': u'A Novel By Tolstoy'},
            'license_id': 'ca-ogl-lgo',
            'resources': [{
                'name': {'en': u'Full text.', 'fr': u'Full text.'},
                'format': u'TXT',
                'url': u'http://www.annakarenina.com/download/',
                'size': 42,
                'resource_type': 'file',
                'language': 'zxx; CAN',
            }],
        }

        cls.complete_pkg = dict(cls.incomplete_pkg,
            owner_org='nrcan-rncan',
            title={'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            frequency=u'as_needed',
            notes={'en': u'...', 'fr': u'...'},
            subject=[u'PE'],
            date_published=u'2013-01-01',
            keywords={'en': [u'book'], 'fr': [u'livre']},
            )

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()

    def test_basic_package(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='basic_package', **self.incomplete_pkg)

        resp = self.normal_action.package_create(
            name='basic_package', **self.complete_pkg)
        assert resp['title']['fr'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['id'])
        assert resp['title']['fr'] == u'Un novel par Tolstoy'

    def test_keyword_validation(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg,
                keywords={'en':['test'], 'fr':['not! ok!']}))

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg,
                keywords={'en':['test'], 'fr':['one too short', 'q']}))

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='keyword_validation',
            **dict(self.complete_pkg,
                keywords={'en':['this is much too long' * 50], 'fr':['test']}))

        self.normal_action.package_create(
            name='keyword_validation',
            **dict(self.complete_pkg,
                keywords={'en':['these', 'ones', 'are', 'a-ok'], 'fr':['test']}))

    def test_custom_dataset_id(self):
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            name='custom_dataset_id', id='my-custom-id', **self.complete_pkg)

        self.sysadmin_action.package_create(
            name='custom_dataset_id', id='my-custom-id', **self.complete_pkg)

        resp = self.action.package_show(id='my-custom-id')
        assert resp['id'] == 'my-custom-id'
        assert resp['name'] == 'custom_dataset_id'

        self.assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            name='different_dataset_id', id='my-custom-id', **self.complete_pkg)

    def test_raw_required(self):
        raw_pkg = dict(self.complete_pkg)
        del raw_pkg['title']

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **raw_pkg)

    def test_tag_extras_bug(self):
        resp = self.normal_action.package_create(
            **self.complete_pkg)

        resp = self.action.package_show(id=resp['id'])
        assert 'subject' not in [e['key'] for e in resp.get('extras',[])]

    def test_keywords_with_apostrophe(self):
        self.normal_action.package_create(
            **dict(self.complete_pkg, keywords=
                {'en': ['test'], 'fr': ["emissions de l'automobile"]}))

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
        pkg = self.normal_action.package_create(**self.complete_pkg)

        # not generated, we set this one but later tests depend on it
        self.assert_equal(pkg['license_id'], 'ca-ogl-lgo')
        # this one is generated in the bowels of CKAN's model_dictize
        self.assert_equal(pkg['license_title'],
            'Open Government Licence - Canada')

        raise SkipTest('XXX: not generating fields yet')
        # some we actually generate ourselves
        self.assert_equal(pkg['license_title_fra'],
            'Licence du gouvernement ouvert - Canada')
        assert pkg['license_url_fra']

        assert pkg['department_number']

    def test_portal_release_date(self):
        raise SkipTest('XXX: portal_release_date not implemented yet')
        release_pkg = dict(self.complete_pkg,
            portal_release_date='2012-01-01')

        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **release_pkg)

        self.publisher_action.package_create(**release_pkg)

        self.sysadmin_action.package_create(**release_pkg)

    def test_spatial(self):
        raise SkipTest('XXX: spatial not implemented in raw schema')
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

    def test_dont_change_portal_release_date(self):
        "normal users should not be able to reset the portal release date"
        raise SkipTest('XXX portal_release_date not yet implemented')

        resp = self.sysadmin_action.package_create(
            portal_release_date='2012-01-01',
            **self.complete_pkg)

        # silently ignore missing portal_release_date
        self.normal_action.package_update(id=resp['id'],
            **self.complete_pkg)

        resp2 = self.normal_action.package_show(id=resp['id'])

        self.assert_equal(resp['portal_release_date'],
            resp2.get('portal_release_date'))

