from ckan.plugins.toolkit import chained_auth_function, h


# block datastore-modifying APIs on the portal
@chained_auth_function
def datastore_create(up_func, context, data_dict):
    if not h.is_registry():
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_delete(up_func, context, data_dict):
    if not h.is_registry():
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def datastore_upsert(up_func, context, data_dict):
    if not h.is_registry():
        return {'success': False}
    return up_func(context, data_dict)

@chained_auth_function
def request_reset(up_func, context, data_dict):
    if not h.is_registry():
        return {'success': False}
    return up_func(context, data_dict)
