# -*- coding: UTF-8 -*-
from ckan.tests.helpers import call_action
from ckan.tests.factories import Sysadmin
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.plugins.toolkit import Invalid

import pytest
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaResource as Resource,
    CanadaUser as User
)

from ckanapi import LocalCKAN, ValidationError
import json

from ckanext.canada.validators import canada_tags


class TestCanadaTags(object):
    def test_simple(self):
        canada_tags(u'hello', {})


    def test_too_short(self):
        with pytest.raises(Invalid) as ie:
            canada_tags(u'h', {})
        err = str(ie.value)
        expected = 'length is less than minimum'
        assert expected in err


    def test_too_long(self):
        with pytest.raises(Invalid) as ie:
            canada_tags(u'z' * 141, {})
        err = str(ie.value)
        expected = 'length is more than maximum'
        assert expected in err


    def test_barely_fits(self):
        canada_tags(u'z' * 140, {})


    def test_comma(self):
        with pytest.raises(Invalid) as ie:
            canada_tags(u'who,me', {})
        err = str(ie.value)
        expected = 'may not contain commas'
        assert expected in err


    def test_strip_whitespace(self):
        assert canada_tags(u'  hello world\n ', {}) == u'hello world'


    def test_consecutive_spaces(self):
        with pytest.raises(Invalid) as ie:
            canada_tags( u'hello  world', {})
        err = str(ie.value)
        expected = 'may not contain consecutive spaces'
        assert expected in err


    def test_punctuation(self):
        canada_tags(u'yes we accept this ´‘’– —:;.!', {})


    def test_symbols(self):
        canada_tags(u'₩₮¬× this is fine too', {})


    def test_control(self):
        with pytest.raises(Invalid) as ie:
            canada_tags(u'hey\bthere', {})
        err = str(ie.value)
        expected = 'may not contain unprintable character'
        assert expected in err


    def test_separator(self):
        with pytest.raises(Invalid) as ie:
            canada_tags(u'one line\u2028two', {})
        err = str(ie.value)
        expected = 'may not contain separator charater'
        assert expected in err


class TestNAVLSchema(object):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        reset_db()
        clear_all()

        self.sysadmin_user = Sysadmin()
        self.normal_user = User()
        self.org = Organization(title_translated = {
                'en': 'en org name',
                'fr': 'fr org name'})

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
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(
                name='12345678-9abc-def0-1234-56789abcdef0',
                **self.incomplete_pkg)
        err = ve.value.error_dict
        expected = ['notes_translated-en',
                    'frequency',
                    'subject',
                    'notes_translated-fr',
                    'keywords-en',
                    'title_translated',
                    'date_published',
                    'keywords-fr',
                    'owner_org']
        for k in set(err):
            assert k in expected

        resp = self.normal_action.package_create(
            name='12345678-9abc-def0-1234-56789abcdef0', **self.complete_pkg)
        assert resp['title_translated']['fr'] == u'Un novel par Tolstoy'

        resp = self.action.package_show(id=resp['id'])
        assert resp['title_translated']['fr'] == u'Un novel par Tolstoy'


    def test_keyword_validation(self):
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**dict(
                self.complete_pkg,
                keywords={'en':['test'], 'fr':['not  ok']}))
        err = ve.value.error_dict
        expected = 'may not contain consecutive spaces'
        assert 'keywords' in err
        assert expected in err['keywords'][0]

        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**dict(
                self.complete_pkg,
                keywords={'en':['test'], 'fr':['one too short', 'q']}))
        err = ve.value.error_dict
        expected = 'length is less than minimum'
        assert 'keywords' in err
        assert expected in err['keywords'][0]

        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**dict(
                self.complete_pkg,
                keywords={'en':['this is much too long' * 50], 'fr':['test']}))
        err = ve.value.error_dict
        expected = 'length is more than maximum'
        assert 'keywords' in err
        assert expected in err['keywords'][0]

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

        with pytest.raises(ValidationError) as ve:
            self.sysadmin_action.package_create(
                name='12345678-9abc-def0-1234-56789abcdef0',
                id=my_uuid,
                **self.complete_pkg)
        err = ve.value.error_dict
        expected = 'Dataset id already exists'
        assert 'id' in err
        assert expected in err['id'][0]

        with pytest.raises(ValidationError) as ve:
            self.sysadmin_action.package_create(
                id='my-custom-id',
                **self.complete_pkg)
        err = ve.value.error_dict
        expected = 'Badly formed hexadecimal UUID string'
        assert 'id' in err
        assert expected in err['id'][0]


    def test_raw_required(self):
        raw_pkg = dict(self.complete_pkg)
        del raw_pkg['title_translated']

        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**raw_pkg)
        err = ve.value.error_dict
        expected = ['title_translated-fr',
                    'title_translated-en']
        for k in set(err):
            assert k in expected


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
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**dict(
                self.complete_pkg,
                resources=[dict(
                    self.complete_pkg['resources'][0],
                    size='10M',)]))
        err = ve.value.error_dict
        expected = 'size'
        assert 'resources' in err
        assert expected in err['resources'][0]


    def test_copy_org_name(self):
        pkg = self.normal_action.package_create(**self.complete_pkg)

        assert sorted(pkg['org_title_at_publication']) == ['en', 'fr']
        assert pkg['org_title_at_publication']['en'] == 'en org name'
        assert pkg['org_title_at_publication']['fr'] == 'fr org name'


    def test_dont_copy_org_name(self):
        pkg = self.normal_action.package_create(**dict(
            self.complete_pkg, org_title_at_publication={'en':'a', 'fr':'b'}))

        assert pkg['org_title_at_publication']['en'] == 'a'
        assert pkg['org_title_at_publication']['fr'] == 'b'


    def test_license_fields(self):
        pkg = self.normal_action.package_create(**self.complete_pkg)

        # not generated, we set this one but later tests depend on it
        assert pkg['license_id'] == 'ca-ogl-lgo'
        # this one is generated in the bowels of CKAN's model_dictize
        assert pkg['license_title'] == 'Open Government Licence - Canada'


    def test_portal_release_date(self):
        release_pkg = dict(self.complete_pkg,
            portal_release_date='2012-01-01')

        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**release_pkg)
        err = ve.value.error_dict
        expected = 'This key is read-only'
        assert 'portal_release_date' in err
        assert expected in err['portal_release_date'][0]

        self.sysadmin_action.package_create(**release_pkg)


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
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**bad_spatial_pkg)
        err = ve.value.error_dict
        expected = 'Invalid GeoJSON'
        assert 'spatial' in err
        assert expected in err['spatial'][0]

        bad_spatial_pkg2 = dict(self.complete_pkg,
            spatial='forty')
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**bad_spatial_pkg2)
        err = ve.value.error_dict
        expected = 'Invalid GeoJSON'
        assert 'spatial' in err
        assert expected in err['spatial'][0]

        bad_spatial_pkg3 = dict(self.complete_pkg,
            spatial='{"type": "Polygon", "coordinates": ''}')
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**bad_spatial_pkg3)
        err = ve.value.error_dict
        expected = 'Invalid GeoJSON'
        assert 'spatial' in err
        assert expected in err['spatial'][0]

        bad_spatial_pkg4 = dict(self.complete_pkg,
            spatial='{"type": "Polygon", "coordinates": [1,2,3,4]}')
        with pytest.raises(ValidationError) as ve:
            self.normal_action.package_create(**bad_spatial_pkg4)
        err = ve.value.error_dict
        expected = 'Invalid GeoJSON'
        assert 'spatial' in err
        assert expected in err['spatial'][0]


    def test_dont_change_portal_release_date(self):
        "normal users should not be able to reset the portal release date"
        resp = self.sysadmin_action.package_create(
            portal_release_date='2012-01-01',
            **self.complete_pkg)

        # silently ignore missing portal_release_date
        self.normal_action.package_update(id=resp['id'],
            **self.complete_pkg)

        resp2 = self.normal_action.package_show(id=resp['id'])

        assert resp['portal_release_date'] == resp2.get('portal_release_date')


    def test_resource_view(self):
        "creating a resource view should default `title` and `title_fr` fields"
        resource_view_data = dict(
            resource_id=Resource()['id'],
            view_type='image_view')

        resp = self.sysadmin_action.resource_view_create(**resource_view_data)

        assert resp['title'] == 'View'
        assert resp['title_fr'] == 'Vue'

        resource_view_data = dict(
            resource_id=Resource()['id'],
            view_type='image_view',
            title='Test Resource View',
            title_fr='Test Resource View FR')

        resp = self.sysadmin_action.resource_view_create(**resource_view_data)

        assert resp['title'] == 'Test Resource View'
        assert resp['title_fr'] == 'Test Resource View FR'
