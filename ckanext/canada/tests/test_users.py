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
        user_dict = self.sysadmin_action.user_create(
            email='example@example.com', name='example', password=make_uuid())

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
        user_dict = self.sysadmin_action.user_create(
            email='example@example.com', name='example', password=make_uuid())

        assert 'default_dataset_visibility' not in user_dict
        assert 'opt_in_features__pd_datatables' not in user_dict

        user_id = self.normal_user['id']

        # user_show should fill in defaults
        user_dict = self.sysadmin_action.user_show(id=user_id)

        assert user_dict['default_dataset_visibility'] == 'private'
        assert user_dict['opt_in_features__pd_datatables'] is False

        user_dict = self.sysadmin_action.user_patch(
            id=user_id, default_dataset_visibility='public',
            opt_in_features__pd_datatables=True)

        assert user_dict['default_dataset_visibility'] == 'public'
        assert user_dict['opt_in_features__pd_datatables'] is True
        assert user_dict['plugin_extras']['default_dataset_visibility'] == 'public'
        assert user_dict['plugin_extras']['opt_in_features__pd_datatables'] is True

        # normal user cannot set default_dataset_visibility
        user_dict = self.normal_action.user_patch(
            id=user_id, default_dataset_visibility='private')

        assert user_dict['default_dataset_visibility'] == 'public'
        assert user_dict['opt_in_features__pd_datatables'] is True

        # own user should be able to update opt_in_features
        user_dict = self.normal_action.user_patch(
            id=user_id, opt_in_features__pd_datatables=False)

        assert user_dict['default_dataset_visibility'] == 'public'
        assert user_dict['opt_in_features__pd_datatables'] is False

        # default_dataset_visibility can only be private or public
        with pytest.raises(ValidationError) as ve:
            user_dict = self.sysadmin_action.user_patch(
                id=user_id, default_dataset_visibility='fail')
        err = ve.value.error_dict

        assert 'default_dataset_visibility' in err
        assert err['default_dataset_visibility'] == ["Value must be one of ['private', 'public']"]
