from ckan.logic.action import get as core_get
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model

from ckan.plugins.toolkit import (
    get_or_bust,
    ValidationError,
    side_effect_free,
    chained_action,
    config,
    ObjectNotFound,
    _,
    g,
    get_action
)
from ckan.authz import is_sysadmin

import functools
from flask import has_request_context

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
    q = q.filter(or_(model.Activity.activity_type.endswith('package'),  # Package create, update, delete
                     model.Activity.activity_type.endswith('view'),  # Resource View create, update, delete
                     model.Activity.activity_type.endswith('created datastore')))  # DataStore create & Data Dictionary update
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
def canada_resource_view_show(up_func, context, data_dict):
    """
    Return the metadata of a resource_view.

    :param id: the id of the resource_view
    :type id: string

    :rtype: dictionary

    Canada Fork: extends the resource_view_show action method
    to prevent showing datatable_views for invalid and inactive Resources

    We need this method to 404 the resource_view page (e.g. viewing in full screen)

    If a user is logged in, we want them to be able to see and edit the datatables_view
    views still. We will just add a key to the view dict to be used within templates for visuals.
    """
    view_dict = up_func(context, data_dict)
    if view_dict.get('view_type') == 'datatables_view':
        # at this point, the core function has been called, calling resource_show
        # and adding the Resource Object into the context
        res_extras = getattr(context.get('resource'), 'extras', {})
        site_user = get_action('get_site_user')({'ignore_auth': True}, {})['name']
        is_system_process = False
        if has_request_context():
            current_user = g.user
        else:
            current_user = None
            is_system_process = True

        if not res_extras.get('datastore_active', False) or \
        res_extras.get('validation_status') != 'success':
            # if the Resource is not active in the DataStore or has not
            # passed validation, we do not want to show its datatables_view views

            if not is_system_process and not current_user:
                # only raise if a user is not logged in
                raise ObjectNotFound

            if not is_system_process and current_user != site_user:
                # only add key/value if not system process
                view_dict['canada_disabled_view'] = True

    return view_dict


@chained_action
def canada_resource_view_list(up_func, context, data_dict):
    """
    Return the list of resource views for a particular resource.

    :param id: the id of the resource
    :type id: string

    :rtype: list of dictionaries.

    Canada Fork: extends the resource_view_list action method
    to prevent showing datatable_views for invalid and inactive Resources

    This will delete any datatables_view from the list of views.

    If a user is logged in, we want them to be able to see and edit the datatables_view
    views still. We will just add a key to the view dict to be used within templates for visuals.
    """
    view_list = up_func(context, data_dict)
    # at this point, the core function has been called, calling resource_show
    # and adding the Resource Object into the context
    res_extras = getattr(context.get('resource'), 'extras', {})
    site_user = get_action('get_site_user')({'ignore_auth': True}, {})['name']
    is_system_process = False
    if has_request_context():
        current_user = g.user
    else:
        current_user = None
        is_system_process = True
    disabled_views_indexes = []
    for i, view_dict in enumerate(view_list):

        if view_dict.get('view_type') == 'datatables_view' and \
        ( not res_extras.get('datastore_active', False) or
          res_extras.get('validation_status') != 'success'):
            # if the Resource is not active in the DataStore or has not
            # passed validation, we do not want to show its datatables_view views

            if not is_system_process and not current_user:
                # only remove from the list if a user is not logged in
                disabled_views_indexes.append(i)
                continue

            if not is_system_process and current_user != site_user:
                # only add key/value if not system process
                view_list[i]['canada_disabled_view'] = True
    return [v for i, v in enumerate(view_list) if i not in disabled_views_indexes]
