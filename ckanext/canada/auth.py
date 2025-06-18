from ckan.types import Context, DataDict, AuthResult

from ckan.plugins.toolkit import config, h
from ckan.authz import has_user_permission_for_group_or_org


def _is_reporting_user(context: Context):
    if not context.get('user') or not config.get('ckanext.canada.reporting_user'):
        return False
    return context.get('user') == config.get('ckanext.canada.reporting_user')


def _registry_org_perms(context: Context, data_dict: DataDict) -> AuthResult:
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


def group_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context, data_dict)


def group_show(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context, data_dict)


def organization_list(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context, data_dict)


def organization_show(context: Context, data_dict: DataDict) -> AuthResult:
    return _registry_org_perms(context, data_dict)


def recently_changed_packages_activity_list(
        context: Context,
        data_dict: DataDict) -> AuthResult:
    """
    Legacy, anyone can view.
    """
    return {'success': True}
