from ckan.logic.action import get as core_get
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model

from ckan.plugins.toolkit import (
    get_or_bust, ValidationError, side_effect_free, get_action, chained_action, config)
from ckan.authz import is_sysadmin

import functools

from sqlalchemy import func
from sqlalchemy import or_


def limit_api_logic():
    """
    Return a dict of logic function names -> wrappers that override
    existing api calls to set new default limits and hard limits
    """
    return {}
    context_limit_packages = {
        'group_show': (5, 20),
        'organization_show': (5, 20),
    }
    data_dict_limit = {
        'package_search': (int(config.get('ckan.datasets_per_page', 20)), 300),
        'package_activity_list': (20, 100),
        'recently_changed_packages_activity_list': (20, 100),
        'package_activity_list_html': (20, 100),
        'dashboard_activity_list': (20, 100),
        'dashboard_activity_list_html': (20, 100),
        }

    out = {}
    for name, (default, limit) in context_limit_packages.items():
        action = getattr(core_get, name)
        @functools.wraps(action)
        def wrapper(context, data_dict,
                default=default, limit=limit, action=action):
            #value = int(context.get('limits', {}).get('packages', default))
            #context.setdefault('limits', {})['packages'] = min(value, limit)
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
            try:
                if int(data_dict.get('offset', '0')) > 1000:
                    return []  # no.
                value = int(data_dict.get(param, default))
            except ValueError:
                return []
            data_dict[param] = min(value, limit)
            return action(context, data_dict)
        if hasattr(action, 'side_effect_free'):
            wrapper.side_effect_free = action.side_effect_free
        out[name] = wrapper

    return out


@side_effect_free
def changed_packages_activity_timestamp_since(context, data_dict):
    '''Return the package_id and timestamp of all recently added or changed packages.

    :param since_time: starting date/time

    Limited to 10,000 records (configurable via the
    ckan.activity_timestamp_since_limit setting) but may be called repeatedly
    with the timestamp of the last record to collect all activities.

    :rtype: list of dictionaries
    '''

    since = get_or_bust(data_dict, 'since_time')
    try:
        since_time = isodate(since, None)
    except Invalid, e:
        raise ValidationError({'since_time':e.error})

    # hard limit this api to reduce opportunity for abuse
    limit = int(config.get('ckan.activity_timestamp_since_limit', 10000))

    package_timestamp_list = []
    for row in _changed_packages_activity_timestamp_since(since_time, limit):
        package_timestamp_list.append({
            'package_id': row.object_id,
            'timestamp': row.timestamp})
    return package_timestamp_list


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


def _changed_packages_activity_timestamp_since(since, limit):
    '''Return package_ids and last activity date of changed package
    activities since a given date.

    This activity stream includes recent 'new package', 'changed package',
    'deleted package', 'new resource view', 'changed resource view' and
    'deleted resource view' activities for the whole site.

    '''
    q = model.Session.query(model.Activity.object_id.label('object_id'),
                            func.max(model.Activity.timestamp).label(
                                'timestamp'))
    q = q.filter(or_(model.Activity.activity_type.endswith('package'),
                     model.Activity.activity_type.endswith('view'),
                     model.Activity.activity_type.endswith('data dictionary')))
    q = q.filter(model.Activity.timestamp > since)
    q = q.group_by(model.Activity.object_id)
    q = q.order_by('timestamp')
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


def datastore_create_temp_user_table(context):
    '''
    Create a table to pass the current username and sysadmin
    state to our triggers for marking modified rows
    '''
    if 'user' not in context:
        return

    from ckanext.datastore.backend.postgres import literal_string
    connection = context['connection']
    username = context['user']
    connection.execute(u'''
        CREATE TEMP TABLE datastore_user (
            username text NOT NULL,
            sysadmin boolean NOT NULL
            ) ON COMMIT DROP;
        INSERT INTO datastore_user VALUES (
            {username}, {sysadmin}
            );
        '''.format(
            username=literal_string(username),
            sysadmin='TRUE' if is_sysadmin(username) else 'FALSE'))


@chained_action
def canada_datastore_create(up_func, context, data_dict):
    """
    Checks if the Data Dictionary (fields) have been updated and creates an Activity if so.
    """
    resource_id = data_dict.get('resource_id', data_dict.get('resource', {}).get('id', None))
    if resource_id:
        new_data_dictionary = data_dict.get('fields', {})
        old_ds_data = get_action('datastore_search')(context, {'resource_id': resource_id, 'limit': 0})

        has_updated_dictionary = False

        if old_ds_data and 'fields' in old_ds_data:

            for field_dict in old_ds_data.get('fields'):
                if field_dict.get('id') == '_id':
                    continue
                if field_dict not in new_data_dictionary:
                    has_updated_dictionary = True
                    break

        if has_updated_dictionary:
            res_dict = get_action('resource_show')(context, {'id': resource_id})
            try:
                user = context['user']
                user_id = model.User.by_name(user.decode('utf8')).id
            except AttributeError:
                # do not create activity for non-users
                pass
            else:
                activity_dict = {
                    'user_id': user_id,
                    'object_id': res_dict['package_id'],
                    'activity_type': 'updated resource data dictionary',
                    'data': {'id': resource_id, 'name_translated': res_dict.get('name_translated'),
                             'package_id': res_dict['package_id']},
                }
                activity_create_context = {
                    'model': model,
                    'user': user,
                    'defer_commit': False,
                    'ignore_auth': True,
                    'session': context['session'],
                }
                get_action('activity_create')(activity_create_context, activity_dict)

    return up_func(context, data_dict)
