# -*- coding: UTF-8 -*-
from ckanapi import LocalCKAN
import ckan.plugins as p

from ckan.tests.helpers import FunctionalTestBase
from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User,
    CanadaDataset as Dataset
)
from ckanext.canada.tests import canada_tests_init_validation


class TestRegistrySearch(FunctionalTestBase):
    """
    Class to test the package_search functionality for the Registry.
    """
    def setup(self):
        canada_tests_init_validation()
        super(TestRegistrySearch, self).setup()
        # all datasets in canada_internal are private
        self.include_private = True
        user = User()
        editor = User()
        sysadmin = Sysadmin()
        self.org = Organization(users=[
            {'name': editor['name'],
             'capacity': 'editor'},
            {'name': sysadmin['name'],
             'capacity': 'admin'}])
        self.user_lc = LocalCKAN(username=user['name'])
        self.editor_lc = LocalCKAN(username=editor['name'])
        self.system_lc = LocalCKAN(username=sysadmin['name'])
        #
        # Datasets 0, 1, 2, and 3
        # 1 & 3 will be ready to publish
        # 3 will not have a portal release date
        # datasets belong to self.org
        #
        for i in range(0, 4):  # 0-3
            Dataset(
                owner_org=self.org['id'],
                title_translated={
                    'en': 'Test Dataset %s' % i,
                    'fr': 'Test FR Dataset %s' % i},
                notes_translated = {
                    'en': 'Test Notes %s' % i,
                    'fr': 'Test FR Notes %s' % i},
                keywords = {
                    'en': ['Test %s' % i, 'Keywords'],
                    'fr': ['Test %s' % i, 'FR', 'Keywords']},
                ready_to_publish=str(i == 1 or i == 3).lower(),
                portal_release_date=None if i == 3 else '2000-01-01')
        self.org2 = Organization()
        #
        # Datasets 4 and 5
        # datasets belong to org2
        #
        for i in range(4, 6):  # 4-5
            Dataset(
                owner_org=self.org2['id'],
                title_translated={
                    'en': 'Test Dataset %s' % i,
                    'fr': 'Test FR Dataset %s' % i},
                notes_translated = {
                    'en': 'Test Notes %s' % i,
                    'fr': 'Test FR Notes %s' % i},
                keywords = {
                    'en': ['Test %s' % i, 'Keywords'],
                    'fr': ['Test %s' % i, 'FR', 'Keywords']},
                ready_to_publish='true',
                portal_release_date='2000-01-01')


    def test_portal_release_date_facet(self):
        response = self.system_lc.action.package_search(
            q='*:*',
            include_private=self.include_private)

        assert 'facet_ranges' in response
        assert 'portal_release_date' in response['facet_ranges']
        assert 'counts' in response['facet_ranges']['portal_release_date']
        assert 5 in response['facet_ranges']['portal_release_date']['counts']


    def test_sysadmin_package_search(self):
        "A sysadmin should have access to all packages."
        response = self.system_lc.action.package_search(
            q='*:*',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 6


    def test_user_package_search(self):
        "A user with no access to Orgs should not see any packages."
        response = self.user_lc.action.package_search(
            q='*:*',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 0


    def test_editor_package_search(self):
        "A user with editor access to an Org should see those organization's packages."
        response = self.editor_lc.action.package_search(
            q='*:*',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 4


    def test_editor_package_search_another_org(self):
        "A user with editor access to an Org should NOT be able to see another organization's packages."
        response = self.editor_lc.action.package_search(
            fq='owner_org:%s' % self.org2['id'],
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 0


class TestPortalSearch(FunctionalTestBase):
    """
    Class to test the package_search functionality for the Portal.
    """
    def setup(self):
        canada_tests_init_validation()
        if p.plugin_loaded('canada_internal'):
            p.unload('canada_internal')
        super(TestPortalSearch, self).setup()
        # datasets on the portal are all public
        self.include_private = False
        self.org = Organization()
        self.lc = LocalCKAN()
        for i in range(0, 4):  # 0-3
            Dataset(
                owner_org=self.org['id'],
                title_translated={
                    'en': 'Test Dataset %s' % i,
                    'fr': 'Test FR Dataset %s' % i},
                notes_translated = {
                    'en': 'Test Notes %s' % i,
                    'fr': 'Test FR Notes %s' % i},
                keywords = {
                    'en': ['Test %s' % i, 'Keywords'],
                    'fr': ['Test %s' % i, 'FR', 'Keywords']},
                ready_to_publish='true',
                portal_release_date='2000-01-01')
        self.org2 = Organization()
        for i in range(4, 6):  # 4-5
            Dataset(
                owner_org=self.org2['id'],
                title_translated={
                    'en': 'Test Dataset %s' % i,
                    'fr': 'Test FR Dataset %s' % i},
                notes_translated = {
                    'en': 'Test Notes %s' % i,
                    'fr': 'Test FR Notes %s' % i},
                keywords = {
                    'en': ['Test %s' % i, 'Keywords'],
                    'fr': ['Test %s' % i, 'FR', 'Keywords']},
                ready_to_publish='true',
                portal_release_date='2000-01-01')


    def test_user_package_search(self):
        response = self.lc.action.package_search(
            q='*:*',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 6


    def test_user_package_search_by_owner_org(self):
        response = self.lc.action.package_search(
            fq='owner_org:%s' % self.org['id'],
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 4

        response = self.lc.action.package_search(
            fq='owner_org:%s' % self.org2['id'],
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 2


    def test_user_package_search_by_keywords(self):
        response = self.lc.action.package_search(
            fq='keywords:("Test 0" OR "Test 1")',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 2

        response = self.lc.action.package_search(
            fq='keywords:("Keywords" "Test 5")',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 1

        response = self.lc.action.package_search(
            fq='keywords:"Keywords"',
            include_private=self.include_private)

        assert 'count' in response
        assert response['count'] == 6
