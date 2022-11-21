from ckan.plugins.toolkit import chained_auth_function, config


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
