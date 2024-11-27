from ckan.logic.action import get as core_get
from ckan.logic.validators import isodate, Invalid
from ckan.lib.dictization import model_dictize
from ckan import model
from contextlib import contextmanager

from redis import ConnectionPool, Redis
from rq import Queue

from datetime import datetime, timedelta

from ckan.plugins.toolkit import (
    get_or_bust,
    ValidationError,
    side_effect_free,
    chained_action,
    config,
    ObjectNotFound,
    NotAuthorized,
    _,
    g,
    get_action,
    h,
    asbool,
    check_access,
)
from ckan.authz import is_sysadmin

import functools
from flask import has_request_context

from sqlalchemy import func
from sqlalchemy import or_

from six.moves.urllib.parse import urlparse
import mimetypes
from ckanext.scheming.helpers import scheming_get_preset

from ckanext.datastore.backend import DatastoreBackend
from ckanext.canada import model as canada_model

MIMETYPES_AS_DOMAINS = [
    'application/x-msdos-program',  # .com
    'application/vnd.lotus-organizer',  # .org
]

from rq.job import Job
from rq.exceptions import NoSuchJobError

from pytz import timezone
from logging import getLogger


log = getLogger(__name__)
ottawa_tz = timezone('America/Montreal')

JOB_MAPPING = {
    'ckanext.validation.jobs.run_validation_job': {
        'icon': 'fa-check-circle',
        'rid': lambda job_args: job_args.get('id'),
    },
    'ckanext.validation.plugin._remove_unsupported_resource_validation_reports': {
        'icon': 'fa-trash',
        'rid': lambda job_args: job_args,
    },
    'ckanext.xloader.jobs.xloader_data_into_datastore': {
        'icon': 'fa-cloud-upload',
        'rid': lambda job_args: job_args.get('metadata', {}).get('resource_id'),
    },
    'ckanext.xloader.plugin._remove_unsupported_resource_from_datastore': {
        'icon': 'fa-trash',
        'rid': lambda job_args: job_args,
    },
    'ckan.lib.search.rebuild': {
        'icon': 'fa-database',
        'gid': lambda job_kwargs: job_kwargs.get('group_id')
    }
}


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
    except Invalid as e:
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
    except Invalid as e:
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


@contextmanager
def datastore_create_temp_user_table(context, drop_on_commit=True):
    """
    Context manager for wrapping DataStore transactions with
    a temporary user table.

    The table is to pass the current username and sysadmin
    state to our triggers for marking modified rows
    """
    # __enter__ of context manager

    if 'user' not in context:
        yield  # yield here, e.g. return None
    else:
        from ckanext.datastore.backend.postgres import literal_string
        username = context['user']
        context['connection'].execute(u'''
            CREATE TEMP TABLE IF NOT EXISTS datastore_user (
                username text NOT NULL,
                sysadmin boolean NOT NULL
                ){drop_statement};
            INSERT INTO datastore_user VALUES (
                {username}, {sysadmin}
                );
            '''.format(
                drop_statement=' ON COMMIT DROP' if drop_on_commit else '',
                username=literal_string(username),
                sysadmin='TRUE' if is_sysadmin(username) else 'FALSE'))
        yield

    # __exit__ of context manager

    if 'user' in context and not drop_on_commit:
        context['connection'].execute(u'''DROP TABLE datastore_user;''')


def canada_guess_mimetype(context, data_dict):
    """
    Returns mimetype based on url, similar to the Core code,
    but will respect the Schema and choice replacements such
    as ["jpg", "jpeg"] and returns value JPG.
    """
    url = data_dict.pop('url', None)
    mimetype, encoding = mimetypes.guess_type(url)

    if not mimetype or mimetype in MIMETYPES_AS_DOMAINS:
        # if we cannot guess the mimetype, check if it is an actual web address
        # and we can set the mimetype to text/html. Uploaded files have only the filename as url,
        # so check scheme to determine if it's an actual web address.
        parsed = urlparse(url)
        if parsed.scheme:
            mimetype = 'text/html'

    if mimetype:
        # run mimetype through core helper to clean format, then
        # check replacements in the scheming choices.
        mimetype = h.unified_resource_format(mimetype)
        fmt_choices = scheming_get_preset('canada_resource_format')['choices']
        for f in fmt_choices:
            if 'mimetype' in f and mimetype == f['mimetype']:
                # core unified_resource_format may not have all of our
                # scheming mimetype choices.
                mimetype = f['value']
            if 'replaces' in f:
                for r in f['replaces']:
                    if mimetype.lower() == r.lower():
                        mimetype = f['value']

    if not mimetype:
        # raise the ValidationError here so that the front-end and back-end will have it.
        raise ValidationError({'format': _('Could not determine a resource format. Please supply a format.')})

    return mimetype


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
    if not asbool(config.get('ckanext.canada.disable_failed_ds_views', False)):
        return view_dict
    if view_dict.get('view_type') == 'datatables_view':
        # at this point, the core function has been called, calling resource_view_show etc.
        # so we can assume that the Resource and View exists here, and that `resource_id` is in view_dict
        resource = model.Resource.get(view_dict.get('resource_id'))
        url_type = getattr(resource, 'url_type', None)
        if url_type in h.datastore_rw_resource_url_types():
            # we don't want to disable views for TableDesigner or Recombinant
            # as those won't have validation reports.
            return view_dict
        res_extras = getattr(resource, 'extras', {})
        site_user = get_action('get_site_user')({'ignore_auth': True}, {})['name']
        is_system_process = False
        if has_request_context():
            try:
                current_user = g.user
            except (TypeError, AttributeError):
                current_user = None
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
    if not asbool(config.get('ckanext.canada.disable_failed_ds_views', False)):
        return view_list
    # at this point, the core function has been called, calling resource_show etc.
    # so we can assume that the Resource exists here, and that `id` is in data_dict
    resource = model.Resource.get(data_dict.get('id'))
    url_type = getattr(resource, 'url_type', None)
    if url_type in h.datastore_rw_resource_url_types():
        # we don't want to disable views for TableDesigner or Recombinant
        # as those won't have validation reports.
        return view_list
    res_extras = getattr(resource, 'extras', {})
    site_user = get_action('get_site_user')({'ignore_auth': True}, {})['name']
    is_system_process = False
    if has_request_context():
        try:
            current_user = g.user
        except (TypeError, AttributeError):
            current_user = None
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


@chained_action
def canada_job_list(up_func, context, data_dict):
    """List enqueued background jobs.

    :param list queues: Queues to list jobs from. If not given then the
        jobs from all queues are listed.

    :param int limit: Number to limit the list of jobs by.

    :param bool ids_only: Whether to return only a list if job IDs or not.

    :returns: The currently enqueued background jobs.
    :rtype: list

    Will return the list in the way that RQ workers will execute the jobs.
    Thus the left most non-empty queue will be emptied firts
    before the next right non-empty one.

    Canada Fork: fetches some more information from the backend Redis
    and parses it and maps it into some more dict entries to be
    used in the custom Job Queue view method and template.
    """
    job_list = up_func(context, data_dict)

    for job in job_list:
        job_args = None
        job_kwargs = None
        try:
            job_obj = Job.fetch(job.get('id'))
            if job_obj.args:
                job_args = job_obj.args[0]
            if job_obj.kwargs:
                job_kwargs = job_obj.kwargs
        except (NoSuchJobError, KeyError):
            continue

        job_title = _(job.get('title', 'Unknown Job'))
        rid = None
        gid = None

        if job_obj.func_name in JOB_MAPPING:
            if job_args:
                rid = JOB_MAPPING[job_obj.func_name]['rid'](job_args)
            if job_kwargs:
                gid = JOB_MAPPING[job_obj.func_name]['gid'](job_kwargs)
            icon = JOB_MAPPING[job_obj.func_name]['icon']
        else:
            job_title = _('Unknown Job')
            icon = 'fa-circle-o-notch'

        job_info = {}
        if rid or gid:
            current_user = get_action('get_site_user')({'ignore_auth': True}, {})['name']
            if has_request_context():
                try:
                    current_user = g.user
                except (TypeError, AttributeError):
                    pass
            if rid:
                try:
                    resource = get_action('resource_show')({'user': current_user}, {'id': rid})
                except (ObjectNotFound, NotAuthorized):
                    continue
                job_info = {'name_translated': resource.get('name_translated'),
                            'resource_id': rid,
                            'url': h.url_for('dataset_resource.read',
                                            id=resource.get('package_id'),
                                            resource_id=rid)}
            if gid:
                try:
                    group = get_action('organization_show')({'user': current_user}, {'id': gid})
                except (ObjectNotFound, NotAuthorized):
                    try:
                        group = get_action('group_show')({'user': current_user}, {'id': gid})
                    except (ObjectNotFound, NotAuthorized):
                        continue
                job_info = {'name_translated': group.get('title_translated'),
                            'group_id': gid,
                            'url': h.url_for('%s.read' % group.get('type'),
                                            id=group.get('name'))}

        job['info'] = job_info
        job['type'] = job_title
        job['icon'] = icon
        job['status'] = job_obj.get_status()

    return job_list


@side_effect_free
def registry_jobs_running(context, data_dict):
    """
    Returns false if the first job in the default queue has not run in the last 18 minutes.

    #TODO: rework this when the Registry moves to public network.
    """
    registry_redis_url = config.get('ckanext.canada.registry_jobs.url')
    registry_redis_prefix = config.get('ckanext.canada.registry_jobs.prefix')

    if not registry_redis_url or not registry_redis_prefix:
        return False

    check_access('registry_jobs_running', context, data_dict)

    _connection_pool = ConnectionPool.from_url(registry_redis_url)
    redis_conn = Redis(connection_pool=_connection_pool)

    fullname = u'ckan:{}:default'.format(registry_redis_prefix)

    queue = Queue(fullname, connection=redis_conn)

    if not queue:
        return False

    jobs = queue.jobs

    if jobs:
        first_job = jobs[0]
        first_created_at = first_job.created_at.strftime(u'%Y-%m-%dT%H:%M:%S')
        if datetime.strptime(first_created_at, '%Y-%m-%dT%H:%M:%S') < (datetime.now() - timedelta(minutes=18)):
            return False

    return True


@chained_action
def canada_datastore_run_triggers(up_func, context, data_dict):
    """
    Wraps datastore_run_triggers action in context manager for DS temp user table.
    """
    if 'connection' not in context:
        backend = DatastoreBackend.get_active_backend()
        context['connection'] = backend._get_write_engine().connect()
    with datastore_create_temp_user_table(context, drop_on_commit=False):
        return up_func(context, data_dict)


@side_effect_free
def portal_sync_info(context, data_dict):
    """
    Returns PackageSync object for a given package_id if it exists.
    """
    package_id = get_or_bust(data_dict, 'id')

    check_access('portal_sync_info', context, data_dict)

    sync_info = canada_model.PackageSync.get(package_id=package_id)

    if not sync_info:
        raise ObjectNotFound(_('No Portal Sync information found for package %s') % package_id)

    # NOTE: never show sync_info.error as it contains stack traces and system information
    return {
        'package_id': sync_info.package_id,
        'last_run': sync_info.last_run,
        'last_successful_sync': sync_info.last_successful_sync,
        'error_on': sync_info.error_on,
    }


@side_effect_free
def list_out_of_sync_packages(context, data_dict):
    """
    Returns a list of out of sync packages on the Portal.

    Based on PackageSync model.
    """
    check_access('list_out_of_sync_packages', context, data_dict)

    sync_infos_count = model.Session.query(canada_model.PackageSync.package_id).filter(canada_model.PackageSync.error_on != None).count()

    out_of_sync_packages = {'count': sync_infos_count, 'results': []}

    if not sync_infos_count:
        return out_of_sync_packages

    limit = data_dict.get('limit', 25)
    offset = data_dict.get('start', 0)
    sync_infos = model.Session.query(canada_model.PackageSync).filter(canada_model.PackageSync.error_on != None).limit(limit).offset(offset)

    for sync_info in sync_infos:
        try:
            pkg_dict = get_action('package_show')({'user': context.get('user')}, {'id': sync_info.package_id})
        except (ObjectNotFound, NotAuthorized):
            continue
        # NOTE: never show sync_info.error as it contains stack traces and system information
        out_of_sync_packages['results'].append({'pkg_dict': pkg_dict, 'last_successful_sync': sync_info.last_successful_sync,
                                                'error_on': sync_info.error_on, 'last_run': sync_info.last_run})

    return out_of_sync_packages
