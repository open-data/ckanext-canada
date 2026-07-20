# -*- coding: UTF-8 -*-
import pytest

from ckanext.canada.tests import CanadaTestBase
from ckan.tests.factories import Sysadmin
from ckanext.canada.tests.factories import CanadaUser as User

from ckanapi import LocalCKAN, ValidationError
from ckan.model.types import make_uuid


class TestUserSchema(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestUserSchema, self).setup_class()

        self.sysadmin_user = Sysadmin()
        self.normal_user = User()

        self.sysadmin_action = LocalCKAN(
            username=self.sysadmin_user['name']).action
        self.normal_action = LocalCKAN(
            username=self.normal_user['name']).action

    def test_user_name_change(self):
        """
        Users cannot change their usernames.
        """
        username = make_uuid()

        user_dict = self.sysadmin_action.user_create(
            email='example+%s@example.com' % username, name=username, password=make_uuid())

        with pytest.raises(ValidationError) as ve:
            user_dict = self.sysadmin_action.user_patch(
                id=user_dict['id'], name='example_updated')
        err = ve.value.error_dict

        assert 'name' in err
        assert err['name'] == ['That login name can not be modified.']

        with pytest.raises(ValidationError) as ve:
            user_dict = self.normal_action.user_patch(
                id=self.normal_user['name'], name='example_updated')
        err = ve.value.error_dict

        assert 'name' in err
        assert err['name'] == ['That login name can not be modified.']

    def test_user_extras(self):
        """
        Custom plugin_extras and Schema should work as expected.
        """
        username = make_uuid()

        user_dict = self.sysadmin_action.user_create(
            email='example+%s@example.com' % username, name=username, password=make_uuid())

        assert 'opt_in_features__pd_datatables' not in user_dict

        user_id = self.normal_user['id']

        # user_show should fill in defaults
        user_dict = self.sysadmin_action.user_show(id=user_id)

        assert user_dict['opt_in_features__pd_datatables'] is False

        user_dict = self.sysadmin_action.user_patch(
            id=user_id,
            opt_in_features__pd_datatables=True)

        assert user_dict['opt_in_features__pd_datatables'] is True
        assert user_dict['plugin_extras']['opt_in_features__pd_datatables'] is True

        # own user should be able to update opt_in_features
        user_dict = self.normal_action.user_patch(
            id=user_id, opt_in_features__pd_datatables=False)

        assert user_dict['opt_in_features__pd_datatables'] is False

        # excluding custom fields should not change their values
        user_dict = self.normal_action.user_patch(
            id=user_id, fullname='Updated Name')

        assert user_dict['opt_in_features__pd_datatables'] is False

        # adding arbitrary key/values is not allowed
        user_dict = self.normal_action.user_patch(
            id=user_id, plugin_extras={'this': 'that'})

        assert user_dict['opt_in_features__pd_datatables'] is False
        assert 'this' not in user_dict

        user_dict = self.sysadmin_action.user_patch(
            id=user_id, plugin_extras={'this': 'that'})

        assert user_dict['opt_in_features__pd_datatables'] is False
        assert 'this' not in user_dict
        assert 'this' not in user_dict['plugin_extras']
