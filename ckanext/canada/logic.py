from ckan.logic.action import get as core_get
from ckan.logic import get_or_bust, ValidationError, side_effect_free
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model

from pylons import config
import functools


def limit_api_logic():
    """
    Return a dict of logic function names -> wrappers
    that override existing api calls to set hard limits on number of
    items returned in each call
    """
    context_limit_packages = {
        'group_show': 2,
        'organization_show': 2,
    }
    data_dict_limit = {
        'user_activity_list': 2,
        'current_package_list_with_resources': 2,
        'group_package_show': 2,
        'package_search': 10,
        'resource_search': 20,
        'package_activity_list': 2,
        'group_activity_list': 2,
        'organization_activity_list': 2,
        'recently_changed_packages_activity_list': 10,
        'user_activity_list_html': 2,
        'package_activity_list_html': 2,
        'group_activity_list_html': 2,
        'organization_activity_list_html': 2,
        'recently_changed_packages_activity_list_html': 10,
        'dashboard_activity_list': 2,
        'dashboard_activity_list_html': 2,
        }

    out = {}
    for name, limit in context_limit_packages.items():
        action = getattr(core_get, name)
        @functools.wraps(action)
        def wrapper(context, data_dict, limit=limit, action=action):
            passed_limit = context.get('limits', {}).get('packages')
            if passed_limit is not None and passed_limit > limit:
                context.getdefault('limits', {})['packages'] = limit
            return action(context, data_dict)
        if hasattr(action, 'side_effect_free'):
            wrapper.side_effect_free = action.side_effect_free
        out[name] = wrapper

    for name, limit in data_dict_limit.items():
        action = getattr(core_get, name)
        @functools.wraps(action)
        def wrapper(context, data_dict, limit=limit, action=action):
            passed_limit = data_dict.get('limit')
            if passed_limit is not None and passed_limit > limit:
                data_dict['limit'] = limit
            return action(context, data_dict)
        if hasattr(action, 'side_effect_free'):
            wrapper.side_effect_free = action.side_effect_free
        out[name] = wrapper

    return out

@side_effect_free
def changed_packages_activity_list_since(context, data_dict):
    '''Return the activity stream of all recently added or changed packages.

    :param since_time: starting date/time

    Limited to 31 records (configurable via the
    ckan.activity_list_hard_limit setting) but may be called repeatedly
    with the timestamp of the last record to collect all activities.

    :rtype: list of dictionaries
    '''

    since = get_or_bust(data_dict, 'since_time')
    try:
        since_time = isodate(since, None)
    except Invalid, e:
        raise ValidationError({'since_time':e.error})

    # hard limit this api to reduce opportunity for abuse
    limit = int(config.get('ckan.activity_list_hard_limit', 63))

    activity_objects = _changed_packages_activity_list_since(
        since_time, limit)
    return model_dictize.activity_list_dictize(activity_objects, context)

@side_effect_free
def activity_list_from_user_since(context, data_dict):
    '''Return the activity stream of all recently added or changed packages.

    :param since_time: starting date/time

    Limited to 31 records (configurable via the
    ckan.activity_list_hard_limit setting) but may be called repeatedly
    with the timestamp of the last record to collect all activities.
       
    :param user_id:  the user of the requested activity list
    
    :rtype: list of dictionaries
    '''

    since = get_or_bust(data_dict, 'since_time')
    user_id = get_or_bust(data_dict, 'user_id')
    try:
        since_time = isodate(since, None)
    except Invalid, e:
        raise ValidationError({'since_time':e.error})

    # hard limit this api to reduce opportunity for abuse
    limit = int(config.get('ckan.activity_list_hard_limit', 63))

    activity_objects = _activities_from_user_list_since(
        since_time, limit,user_id)
    return model_dictize.activity_list_dictize(activity_objects, context)

def _changed_packages_activity_list_since(since, limit):
    '''Return the site-wide stream of changed package activities since a given
    date.

    This activity stream includes recent 'new package', 'changed package' and
    'deleted package' activities for the whole site.

    '''
    q = model.activity._changed_packages_activity_query()
    q = q.order_by(model.Activity.timestamp)
    q = q.filter(model.Activity.timestamp > since)
    return q.limit(limit)

def _activities_from_user_list_since(since, limit,user_id):
    '''Return the site-wide stream of changed package activities since a given
    date for a particular user.

    This activity stream includes recent 'new package', 'changed package' and
    'deleted package' activities for that user.

    '''
    
    q = model.activity._activities_from_user_query(user_id)
    q = q.order_by(model.Activity.timestamp)
    q = q.filter(model.Activity.timestamp > since)
    return q.limit(limit)
