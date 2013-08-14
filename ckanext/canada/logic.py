from ckan.logic.action import get as core_get
from ckan.logic import get_or_bust, ValidationError, side_effect_free
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model

from pylons import config
import functools


def limit_api_logic():
    """
    Return a dict of logic function names -> wrappers that override
    existing api calls to set new default limits and hard limits
    """
    context_limit_packages = {
        'group_show': (5, 20),
        'organization_show': (5, 20),
    }
    data_dict_limit = {
        'user_activity_list': (20, 100),
        'current_package_list_with_resources': (20, 100),
        'group_package_show': (20, 100),
        'package_search': (20, 100),
        'resource_search': (20, 100),
        'package_activity_list': (20, 100),
        'group_activity_list': (20, 100),
        'organization_activity_list': (20, 100),
        'recently_changed_packages_activity_list': (20, 100),
        'user_activity_list_html': (20, 100),
        'package_activity_list_html': (20, 100),
        'group_activity_list_html': (20, 100),
        'organization_activity_list_html': (20, 100),
        'recently_changed_packages_activity_list_html': (20, 100),
        'dashboard_activity_list': (20, 100),
        'dashboard_activity_list_html': (20, 100),
        }

    out = {}
    for name, (default, limit) in context_limit_packages.items():
        action = getattr(core_get, name)
        @functools.wraps(action)
        def wrapper(context, data_dict,
                default=default, limit=limit, action=action):
            value = int(context.get('limits', {}).get('packages', default))
            context.setdefault('limits', {})['packages'] = min(value, limit)
            return action(context, data_dict)
        if hasattr(action, 'side_effect_free'):
            wrapper.side_effect_free = action.side_effect_free
        out[name] = wrapper

    for name, (default, limit) in data_dict_limit.items():
        action = getattr(core_get, name)
        # package_search is special... :-(
        param = 'rows' if name == 'package_search' else 'limit'
        @functools.wraps(action)
        def wrapper(context, data_dict,
                default=default, limit=limit, action=action, param=param):
            value = int(data_dict.get(param, default))
            data_dict[param] = min(value, limit)
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
