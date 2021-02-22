def inventory_votes_show(context, data_dict):
    '''
    this endpoint is sysadmin only
    nightly data is published as part of inventory csv
    '''
    return {'success': False}

# resource view editing for sysadmin only, for now
def resource_view_create(context, data_dict):
    return {'success': False}

def resource_view_update(context, data_dict):
    return {'success': False}

def resource_view_delete(context, data_dict):
    return {'success': False}
