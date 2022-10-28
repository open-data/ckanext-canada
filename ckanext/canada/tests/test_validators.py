# -*- coding: UTF-8 -*-
from ckan.tests.helpers import FunctionalTestBase, call_action
from ckan.tests import factories
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.plugins.toolkit import Invalid
from ckanext.canada.tests.factories import CanadaOrganization as Organization

from ckanapi import LocalCKAN, ValidationError
import json
from nose.plugins.skip import SkipTest
from nose.tools import assert_raises, assert_equal

from ckanext.canada.validators import canada_tags


class TestCanadaTags(object):
    def test_simple(self):
        canada_tags(u'hello', {})

    def test_too_short(self):
        assert_raises(Invalid, canada_tags, u'h', {})

    def test_too_long(self):
        assert_raises(Invalid, canada_tags, u'z' * 141, {})

    def test_barely_fits(self):
        canada_tags(u'z' * 140, {})

    def test_comma(self):
        assert_raises(Invalid, canada_tags, u'who,me', {})

    def test_strip_whitespace(self):
        assert_equal(canada_tags(u'  hello world\n ', {}), u'hello world')

    def test_consecutive_spaces(self):
        assert_raises(Invalid, canada_tags, u'hello  world', {})

    def test_punctuation(self):
        canada_tags(u'yes we accept this ´‘’– —:;.!', {})

    def test_symbols(self):
        canada_tags(u'₩₮¬× this is fine too', {})

    def test_control(self):
        assert_raises(Invalid, canada_tags, u'hey\bthere', {})

    def test_separator(self):
        assert_raises(Invalid, canada_tags, u'one line\u2028two', {})


class TestNAVLSchema(FunctionalTestBase):

    def setup(self):
        self.sysadmin_user = factories.Sysadmin()
        self.normal_user = factories.User()
        self.org = Organization(title_translated = {
            'en': 'en org name',
            'fr': 'fr org name'
        })

        self.sysadmin_action = LocalCKAN(
            username=self.sysadmin_user['name']).action
        self.normal_action = LocalCKAN(
            username=self.normal_user['name']).action
        self.action = LocalCKAN().action

        self.sysadmin_action.organization_member_create(
            username=self.normal_user['name'],
            id=self.org['name'],
            role='editor')

        self.incomplete_pkg = {
            'type': 'dataset',
            'collection': 'primary',
            'title_translated': {'en': u'A Novel By Tolstoy'},
            'license_id': 'ca-ogl-lgo',
            'ready_to_publish': 'true',
            'imso_approval': 'true',
            'jurisdiction': 'federal',
            'maintainer_email': 'not@all.example.com',
            'restrictions': 'unrestricted',
            'resources': [{
                'name_translated': {'en': u'Full text.', 'fr': u'Full text.'},
                'format': u'TXT',
                'url': u'http://www.annakarenina.com/download/',
                'size': 42,
                'resource_type': 'dataset',
                'language': ['zxx'],
            }],
        }

        self.complete_pkg = dict(self.incomplete_pkg,
            owner_org=self.org['name'],
            title_translated={
                'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            frequency=u'as_needed',
            notes_translated={'en': u'...', 'fr': u'...'},
            subject=[u'persons'],
            date_published=u'2013-01-01',
            keywords={'en': [u'book'], 'fr': [u'livre']},
            )

    def test_basic_package(self):
        assert_raises(ValidationError,
            self.normal_action.package_create,
            name='12345678-9abc-def0-1234-56789abcdef0', **self.incomplete_pkg)

        resp = self.normal_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef0', **self.complete_pkg)
        assert resp['title_translated']['fr'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['id'])
        assert resp['title_translated']['fr'] == u'Un novel par Tolstoy'

    def test_keyword_validation(self):
        assert_raises(ValidationError,
            self.normal_action.package_create,
            **dict(self.complete_pkg,
                keywords={'en':['test'], 'fr':['not  ok']}))

        assert_raises(ValidationError,
            self.normal_action.package_create,
            **dict(self.complete_pkg,
                keywords={'en':['test'], 'fr':['one too short', 'q']}))

        assert_raises(ValidationError,
            self.normal_action.package_create,
            **dict(self.complete_pkg,
                keywords={'en':['this is much too long' * 50], 'fr':['test']}))

        self.normal_action.package_create(
            **dict(self.complete_pkg,
                keywords={'en':['these', 'ones', 'are', 'a-ok'], 'fr':['test']}))

    def test_custom_dataset_id(self):
        my_uuid = '3056920043b943f1a1fb9e7974cbb997'
        norm_uuid = '30569200-43b9-43f1-a1fb-9e7974cbb997'
        self.normal_action.package_create(
            name='02345678-9abc-def0-1234-56789abcdef0', id=my_uuid, **self.complete_pkg)

        resp = self.action.package_show(id='02345678-9abc-def0-1234-56789abcdef0')
        assert resp['id'] == norm_uuid
        assert resp['name'] == '02345678-9abc-def0-1234-56789abcdef0'

        assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            name='12345678-9abc-def0-1234-56789abcdef0', id=my_uuid, **self.complete_pkg)

        assert_raises(ValidationError,
            self.sysadmin_action.package_create,
            id='my-custom-id', **self.complete_pkg)

    def test_raw_required(self):
        raw_pkg = dict(self.complete_pkg)
        del raw_pkg['title_translated']

        assert_raises(ValidationError,
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

    def test_invalid_resource_size(self):
        assert_raises(ValidationError,
            self.normal_action.package_create,
            **dict(self.complete_pkg,
                resources = [dict(self.complete_pkg['resources'][0],
                    size='10M',
                    )],
                )
            )

    def test_copy_org_name(self):
        pkg = self.normal_action.package_create(**self.complete_pkg)

        assert_equal(sorted(pkg['org_title_at_publication']), ['en', 'fr'])
        assert_equal(pkg['org_title_at_publication']['en'], 'en org name')
        assert_equal(pkg['org_title_at_publication']['fr'], 'fr org name')

    def test_dont_copy_org_name(self):
        pkg = self.normal_action.package_create(**dict(
            self.complete_pkg, org_title_at_publication={'en':'a', 'fr':'b'}))

        assert_equal(pkg['org_title_at_publication']['en'], 'a')
        assert_equal(pkg['org_title_at_publication']['fr'], 'b')

    def test_generated_fields(self):
        pkg = self.normal_action.package_create(**self.complete_pkg)

        # not generated, we set this one but later tests depend on it
        assert_equal(pkg['license_id'], 'ca-ogl-lgo')
        # this one is generated in the bowels of CKAN's model_dictize
        assert_equal(pkg['license_title'],
            'Open Government Licence - Canada')

        raise SkipTest('XXX: not generating fields yet')
        # some we actually generate ourselves
        assert_equal(pkg['license_title_fra'],
            'Licence du gouvernement ouvert - Canada')
        assert pkg['license_url_fra']

        assert pkg['department_number']

    def test_portal_release_date(self):
        raise SkipTest('XXX: portal_release_date not implemented yet')
        release_pkg = dict(self.complete_pkg,
            portal_release_date='2012-01-01')

        assert_raises(ValidationError,
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
        assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg)

        bad_spatial_pkg2 = dict(self.complete_pkg,
            spatial='forty')
        assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg2)

        bad_spatial_pkg3 = dict(self.complete_pkg,
            spatial='{"type": "Polygon"}')
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg3)

        bad_spatial_pkg4 = dict(self.complete_pkg,
            spatial='{"type": "Polygon", "coordinates": [1,2,3,4]}')
        self.assert_raises(ValidationError,
            self.normal_action.package_create,
            **bad_spatial_pkg4)

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

        assert_equal(resp['portal_release_date'],
            resp2.get('portal_release_date'))

