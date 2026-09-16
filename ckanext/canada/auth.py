from typing import Dict, Union
from ckan.types import Context, DataDict, AuthResult, AuthFunction, ChainedAuthFunction

from ckan.plugins.toolkit import config, h, auth_allow_anonymous_access
from ckan.authz import has_user_permission_for_group_or_org


def get_auth_methods() -> Dict[str, Union[AuthFunction,
                                          ChainedAuthFunction]]:
    """
    Returns a dict of registered authentication methods.
    """
    return {
        'group_list': group_list,
        'group_show': group_show,
        'organization_list': organization_list,
        'organization_show': organization_show,
        'view_org_members': view_org_members,
        'recently_changed_packages_activity_list':
            recently_changed_packages_activity_list,
        'dcat_auth': dcat_auth,
    }


# type_ignore_reason: underscored method
def _is_reporting_user(context: Context):  # type: ignore
    if not context.get('user') or not config.get('ckanext.canada.reporting_user'):
        return False
    return context.get('user') == config.get('ckanext.canada.reporting_user')


def _registry_org_perms(context: Context) -> AuthResult:
    try:
        if h.is_registry_domain():
            return {'success': bool(context.get('user'))}
    except RuntimeError:
        pass
    return {'success': True}


def view_org_members(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')
    can_view = has_user_permission_for_group_or_org(
        data_dict.get('id'), user, 'manage_group')
    return {'success': can_view}


@auth_allow_anonymous_access
def group_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context)


@auth_allow_anonymous_access
def group_show(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context)


@auth_allow_anonymous_access
def organization_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context)


@auth_allow_anonymous_access
def organization_show(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context)


@auth_allow_anonymous_access
def recently_changed_packages_activity_list(
        context: Context,
        data_dict: DataDict) -> AuthResult:
    """
    Legacy, anyone can view.
    """
    return {'success': True}


@auth_allow_anonymous_access
def dcat_auth(context: Context,
              data_dict: DataDict) -> AuthResult:
    """
    Override dcat_auth, only allowed on the Portal
    """
    try:
        return {'success': not h.is_registry_domain()}
    except RuntimeError:
        pass
    return {'success': True}
