from ckan.logic.action import get as core_get
from ckan.logic import get_or_bust, ValidationError, side_effect_free
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model

from pylons import config

def group_show(context, data_dict):
    """Limit packages returned with groups"""
    context.update({'limits': {'packages': 2}})
    return core_get.group_show(context, data_dict)

def organization_show(context, data_dict):
    """Limit packages returned with organizations"""
    context.update({'limits': {'packages': 2}})
    return core_get.organization_show(context, data_dict)

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
    limit = int(config.get('ckan.activity_list_hard_limit', 31))

    activity_objects = _changed_packages_activity_list_since(
        since_time, limit)
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
