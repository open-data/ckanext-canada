from ckan.plugins.toolkit import (chained_auth_function,
                                  auth_allow_anonymous_access,
                                  config,
                                  request)
from ckan.authz import has_user_permission_for_group_or_org, is_sysadmin
from ckanext.canada.helpers import registry_network_access


def _is_reporting_user(context):
    if not context.get('user') or not config.get('ckanext.canada.reporting_user'):
        return False
    return context.get('user') == config.get('ckanext.canada.reporting_user')

# block datastore-modifying APIs on the portal
@chained_auth_function
def datastore_create(up_func, context, data_dict):
    if 'canada_internal' not in config.get('ckan.plugins'):
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_delete(up_func, context, data_dict):
    if 'canada_internal' not in config.get('ckan.plugins'):
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_upsert(up_func, context, data_dict):
    if 'canada_internal' not in config.get('ckan.plugins'):
        return {'success': False}
    return up_func(context, data_dict)


@chained_auth_function
@auth_allow_anonymous_access
def user_create(up_func, context, data_dict=None):
    # additional check to ensure user can access the Request an Account page
    # only possible if accessing from GOC network
    if not registry_network_access():
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
