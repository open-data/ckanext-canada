# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckan.tests.factories import Sysadmin
from ckan.plugins.toolkit import NotAuthorized, config

import pytest
from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User
)

from ckanapi import LocalCKAN
from ckan import model


class TestSysadminUpdate(CanadaTestBase):
    @classmethod
    def setup_method(self, method):
        """Method is called at class level before EACH test methods of the class are called.
        Setup any state specific to the execution of the given class methods.
        """
        super(TestSysadminUpdate, self).setup_method(method)

        self.sysadmin_user = Sysadmin()
        self.normal_user = User()
        self.org= Organization()

        self.sysadmin_action = LocalCKAN(
            username=self.sysadmin_user['name']).action
        self.normal_action = LocalCKAN(
            username=self.normal_user['name']).action
        self.action = LocalCKAN().action

        # make sysadmin_user a org member
        self.sysadmin_action.organization_member_create(
            username=self.sysadmin_user['name'],
            id=self.org['name'],
            role='admin')

        # make normal_user a org member
        self.sysadmin_action.organization_member_create(
            username=self.normal_user['name'],
            id=self.org['name'],
            role='editor')


    def test_user_cannot_update_sysadmin(self):
        """non sysadmins shoud not be able to update"""
        with pytest.raises(NotAuthorized) as err:
            self.normal_action.user_patch(id=self.sysadmin_user.get('id'),
                                          sysadmin=False)
        assert err
        assert 'not authorized to edit user' in str(err)


    def test_cannot_update_self_sysadmin(self):
        """cannot change your own sysadmin privs"""
        with pytest.raises(NotAuthorized) as err:
            self.sysadmin_action.user_patch(id=self.sysadmin_user.get('id'),
                                            sysadmin=False)
        assert err
        assert 'Cannot modify your own sysadmin privileges' in str(err)


    def test_cannot_update_system_sysadmin(self):
        """cannot change system user privs"""
        site_id = config.get('ckan.site_id')
        with pytest.raises(NotAuthorized) as err:
            self.sysadmin_action.user_patch(id=site_id,
                                            sysadmin=False)
        assert err
        assert 'Cannot modify sysadmin privileges for system user' in str(err)


    def test_update_sysadmin_users(self):
        """tbs member w/ email sysadmin should be able to update"""
        user_dict = self.sysadmin_action.user_patch(id=self.normal_user.get('id'),
                                                    sysadmin=True)
        # user dict does not contain sysadmin, so go get db object
        user_obj = model.User.get(user_dict.get('id'))
        assert user_obj.sysadmin == True


    def test_update_system_sysadmin(self):
        """system user should be able to update"""
        user_dict = self.action.user_patch(id=self.normal_user.get('id'),
                                           sysadmin=True)
        # user dict does not contain sysadmin, so go get db object
        user_obj = model.User.get(user_dict.get('id'))
        assert user_obj.sysadmin == True
