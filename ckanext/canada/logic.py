from ckan.logic.action import get as core_get

def group_show(context, data_dict):
    """Limit packages returned with groups"""
    context.update({'limits': {'packages': 2}})
    return core_get.group_show(context, data_dict)

def organization_show(context, data_dict):
    """Limit packages returned with organizations"""
    context.update({'limits': {'packages': 2}})
    return core_get.organization_show(context, data_dict)
