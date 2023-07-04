from ckantoolkit import h
from ckan.logic import get_action
from ckan.common import _, ungettext
from ckan.lib.helpers import url_for
import datetime
import ckan.logic as logic
import ckan.lib.dictization.model_dictize as model_dictize
from ckan.plugins.toolkit import side_effect_free

MERGE_ACTIVITIES_WITHIN_SECONDS = 2


def datastore_activity_create(context, act_data):
    activity_type = act_data['activity_type']
    count = act_data['count']
    resource_id = act_data['resource_id']
    user = context['user']
    model = context['model']
    user_id = model.User.by_name(user.decode('utf8')).id
    if activity_type == 'deleted datastore':
        #  get last deleted activity for this user, if within 2 seconds,
        #   merge these activities
        act = model.activity.user_activity_list(user_id, 1, 0)
        now = datetime.datetime.now()
        if act and len(act)>0 and (
                now - act[0].timestamp).total_seconds()<MERGE_ACTIVITIES_WITHIN_SECONDS and (
                act[0].activity_type == activity_type):
            act = act[0]
            act.data['count'] += count
            #avoid version
            model.Session.query(model.Activity).filter_by(id=act.id).update(
                {"data": act.data})
            model.Session.refresh(act)
            model.Session.flush()
            model.repo.commit()
            return
    res_obj = model.Resource.get(resource_id)
    pkg = model.Package.get(res_obj.package_id)
    org = model.Group.get(pkg.owner_org)
    activity_dict = {
        'user_id': user_id,
        'object_id': res_obj.package_id,
        'activity_type': activity_type,
    }
    activity_dict['data'] = {
        'resource_id': resource_id,
        'pkg_type': pkg.type,
        'resource_name': res_obj.name,
        'owner_org': org.name,
        'count': count,
    }
    activity_create_context = {
        'model': context['model'],
        'user': context['user'],
        'defer_commit': False,
        'ignore_auth': True,
        'session': context['session'],
    }
    get_action('activity_create')(activity_create_context, activity_dict)


@logic.validate(logic.schema.default_dashboard_activity_list_schema)
@side_effect_free
def recently_changed_packages_activity_list(context, data_dict):
    '''Copied from ckan/ckan/logic/action/get.py
    Custom: Sets include_data to True
    TODO: Remove this action override in CKAN 2.10 upgrade

    Return the activity stream of all recently added or changed packages.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31`` unless set in site's configuration
        ``ckan.activity_list_limit``, upper limit: ``100`` unless set in
        site's configuration ``ckan.activity_list_limit_max``)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    model = context['model']
    offset = data_dict.get('offset', 0)
    data_dict['include_data'] = True
    limit = data_dict['limit']  # defaulted, limited & made an int by schema

    activity_objects = \
        model.activity.recently_changed_packages_activity_list(
            limit=limit, offset=offset)

    return model_dictize.activity_list_dictize(
        activity_objects, context,
        include_data=data_dict['include_data'])
