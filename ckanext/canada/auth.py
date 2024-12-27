from ckan.types import Context, AuthFunction, ChainedAuthFunction, DataDict, AuthResult

from ckan.plugins.toolkit import chained_auth_function, config
from ckan.authz import has_user_permission_for_group_or_org
from ckan.plugins import plugin_loaded


def _is_reporting_user(context: Context):
    if not context.get('user') or not config.get('ckanext.canada.reporting_user'):
        return False
    return context.get('user') == config.get('ckanext.canada.reporting_user')


# block datastore-modifying APIs on the portal
@chained_auth_function
def datastore_create(up_func: AuthFunction, context: Context,
                     data_dict: DataDict) -> ChainedAuthFunction:
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)


@chained_auth_function
def datastore_delete(up_func: AuthFunction, context: Context,
                     data_dict: DataDict) -> ChainedAuthFunction:
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)


@chained_auth_function
def datastore_upsert(up_func: AuthFunction, context: Context,
                     data_dict: DataDict) -> ChainedAuthFunction:
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)


def view_org_members(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get('user')
    can_view = has_user_permission_for_group_or_org(
        data_dict.get('id'), user, 'manage_group')
    return {'success': can_view}


def registry_jobs_running(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': _is_reporting_user(context)}


def group_list(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': bool(context.get('user'))}


def group_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': bool(context.get('user'))}


def organization_list(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': bool(context.get('user'))}


def organization_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': bool(context.get('user'))}


def recently_changed_packages_activity_list(
        context: Context,
        data_dict: DataDict) -> AuthResult:
    """
    Legacy, anyone can view.
    """
    return {'success': True}


def portal_sync_info(context: Context, data_dict: DataDict) -> AuthResult:
    """
    Registry users have to be logged in.

    Anyone on public Portal can access.
    """
    if plugin_loaded('canada_internal'):
        return {'success': bool(context.get('user'))}
    return {'success': True}


def list_out_of_sync_packages(context: Context,
                              data_dict: DataDict) -> AuthResult:
    """
    Only sysadmins can list the out of sync packages.
    """
    return {'success': False}
