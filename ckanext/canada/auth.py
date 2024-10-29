from ckan.plugins.toolkit import chained_auth_function, config
from ckan.authz import has_user_permission_for_group_or_org, is_sysadmin
from ckan.plugins import plugin_loaded


def _is_reporting_user(context):
    if not context.get('user') or not config.get('ckanext.canada.reporting_user'):
        return False
    return context.get('user') == config.get('ckanext.canada.reporting_user')

# block datastore-modifying APIs on the portal
@chained_auth_function
def datastore_create(up_func, context, data_dict):
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_delete(up_func, context, data_dict):
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_upsert(up_func, context, data_dict):
    if not plugin_loaded('canada_internal'):
        return {'success': False}
    return up_func(context, data_dict)


def view_org_members(context, data_dict):
    user = context.get('user')
    can_view = has_user_permission_for_group_or_org(data_dict.get(u'id'), user, 'manage_group')
    return {'success': can_view}


def registry_jobs_running(context, data_dict):
    return {'success': _is_reporting_user(context)}


def group_list(context, data_dict):
    return {'success': bool(context.get('user'))}


def group_show(context, data_dict):
    return {'success': bool(context.get('user'))}


def organization_list(context, data_dict):
    return {'success': bool(context.get('user'))}


def organization_show(context, data_dict):
    return {'success': bool(context.get('user'))}


def recently_changed_packages_activity_list(context, data_dict):
    """
    Legacy, anyone can view.
    """
    return {'success': True}


def portal_sync_info(context, data_dict):
    """
    Registry users have to be logged in.

    Anyone on public Portal can access.
    """
    if plugin_loaded('canada_internal'):
        return {'success': bool(context.get('user'))}
    return {'success': True}


def list_out_of_sync_packages(context, data_dict):
    """
    Only sysadmins can list the out of sync packages.
    """
    return {'success': False}
