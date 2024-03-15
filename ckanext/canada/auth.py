from ckan.plugins.toolkit import chained_auth_function, config
from ckan.authz import has_user_permission_for_group_or_org, is_sysadmin


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


def view_org_members(context, data_dict):
    user = context.get('user')
    can_view = has_user_permission_for_group_or_org(data_dict.get(u'id'), user, 'manage_group')
    return {'success': can_view}
