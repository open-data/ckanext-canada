from ckantoolkit import h
from ckan.logic import get_action
from ckan.common import _
from ckan.lib.helpers import url_for
import datetime


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
                now - act[0].timestamp).total_seconds()<2 and (
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

def get_snippet_datastore(activity, detail):
    if activity['data'].get('pkg_type'):
        org_name = activity['data']['owner_org']
        resource_name = activity['data']['resource_name']
        url = url_for(resource_name=resource_name,owner_org=org_name,
            action='preview_table',
            controller='ckanext.recombinant.controller:UploadController')
        chromo = h.recombinant_get_chromo(resource_name)
        return ''.join(['<a href="', url, '">', _(chromo['title']), '</a>'])
    else:
        return ''


def get_snippet_datastore_detail(activity, detail):
    count = activity['data']['count']
    return ''.join([' ', str(count), ' ', _('entries')])

def activity_stream_string_changed_datastore(context, activity):
    return _("{actor} updated the record {datastore} {datastore_detail}")

def activity_stream_string_deleted_datastore(context, activity):
    return _("{actor} deleted the record {datastore} {datastore_detail}")
