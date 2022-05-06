from ckan.plugins.toolkit import chained_auth_function
from pylons import config

def inventory_votes_show(context, data_dict):
    '''
    this endpoint is sysadmin only
    nightly data is published as part of inventory csv
    '''
    return {'success': False}

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
