# -*- coding: UTF-8 -*-
from ckanext.canada.tests import CanadaTestBase
from ckan.tests.helpers import change_config
from ckan.logic import _actions, check_access

from ckan.plugins.toolkit import NotAuthorized, ValidationError

from ckanext.canada.tests.factories import (
    CanadaOrganization as Organization,
    CanadaUser as User,
    CanadaSysadminWithToken as Sysadmin
)


class TestCanadaAuth(CanadaTestBase):
    @classmethod
    def setup_class(self):
        """Method is called at class level once the class is instatiated.
        Setup any state specific to the execution of the given class.
        """
        super(TestCanadaAuth, self).setup_class()

        self.sysadmin = Sysadmin()
        self.org_admin = User()
        self.editor = User()
        self.member = User()
        Organization(users=[{
            'name': self.sysadmin['name'],
            'capacity': 'admin'},
           {'name': self.org_admin['name'],
            'capacity': 'admin'},
           {'name': self.editor['name'],
            'capacity': 'editor'},
           {'name': self.member['name'],
            'capacity': 'member'}])

    @change_config('ckan.site_read_only', True)
    def test_site_read_only_mode(self):
        """
        When the site is in read only mode, only sysadmins should be able to:
            - _create actions
            - _updated actions
            - _patch actions
            - _delete actions
        """
        name_patterns = [
            '_create',
            '_patch',
            '_update',
            '_delete',
            '_purge',
            '_revise',
            '_reset',
            '_throttle',
            '_submit',
            '_run',
            'send_',
            '_mark_',
            '_clear',
            '_cancel',
            '_revoke',
            '_reorder',
            '_invite',
            '_upsert',
            '_insert',
            'job_list',  # special case for Canada plugin
        ]

        # org admins cannot do things
        for action_func_name, action_func in _actions.items():
            if getattr(action_func, 'side_effect_free', False):
                continue
            try:
                check_access(action_func_name, {'user': self.org_admin['name']}, {})
            except (KeyError, ValueError, ValidationError):
                continue
            except NotAuthorized as e:
                assert any(p in action_func_name for p in name_patterns)
                assert e.message == 'Site is in read only mode'

        # editors cannot do things
        for action_func_name, action_func in _actions.items():
            if getattr(action_func, 'side_effect_free', False):
                continue
            try:
                check_access(action_func_name, {'user': self.editor['name']}, {})
            except (KeyError, ValueError, ValidationError):
                continue
            except NotAuthorized as e:
                assert any(p in action_func_name for p in name_patterns)
                assert e.message == 'Site is in read only mode'

        # members cannot do things
        for action_func_name, action_func in _actions.items():
            if getattr(action_func, 'side_effect_free', False):
                continue
            try:
                check_access(action_func_name, {'user': self.member['name']}, {})
            except (KeyError, ValueError, ValidationError):
                continue
            except NotAuthorized as e:
                assert any(p in action_func_name for p in name_patterns)
                assert e.message == 'Site is in read only mode'

        # sysadmins can do anything still
        for action_func_name, action_func in _actions.items():
            if getattr(action_func, 'side_effect_free', False):
                continue
            try:
                check_access(action_func_name, {'user': self.sysadmin['name']}, {})
            except (KeyError, ValueError, ValidationError):
                continue

        # using ignore_auth can do anything still
        for action_func_name, action_func in _actions.items():
            if getattr(action_func, 'side_effect_free', False):
                continue
            try:
                check_access(action_func_name, {'user': self.member['name'],
                                                'ignore_auth': True}, {})
            except (KeyError, ValueError, ValidationError):
                continue
