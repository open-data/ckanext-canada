import json
import webhelpers.feedgenerator

from ckan.plugins.toolkit import (
    abort,
    get_action,
    config,
    _,
    h,
    c,
    check_access,
    aslist,
    request,
    render
)

from ckan.views.dataset import EditView as DatasetEditView
from ckan.views.resource import EditView as ResourceEditView
from ckan.views.resource import CreateView as ResourceCreateView
from ckan.views.feed import (
    _alternate_url,
    BASE_URL,
    _feed_url,
    CKANFeed,
    output_feed,
    _create_atom_id,
    _navigation_urls,
    _package_search,
    _parse_url_params,
    SITE_TITLE
)

from ckan.authz import is_sysadmin
from ckan.logic import parse_params

from ckan.lib.base import model
from ckan.logic import NotFound
from ckan.lib.helpers import url, date_str_to_datetime

from ckanext.recombinant.datatypes import canonicalize
from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.errors import RecombinantException

from ckanapi import LocalCKAN, NotAuthorized, ValidationError

from flask import Blueprint, make_response

from ckanext.canada.urlsafe import url_part_unescape
from ckanext.canada.controller import notice_no_access

canada_views = Blueprint('canada', __name__)
canada_feeds = Blueprint(u'canada_feeds', __name__, url_prefix=u'/feeds')

class IntentionalServerError(Exception):
    pass


def login():
    from ckan.views.user import _get_repoze_handler

    came_from = h.url_for(u'canada.logged_in')
    c.login_handler = h.url_for(
        _get_repoze_handler(u'login_handler_path'), came_from=came_from)
    return render(u'user/login.html', {})


def logged_in():
    if c.user:
        user_dict = get_action('user_show')(None, {'id': c.user})

        h.flash_success(
            _('<strong>Note</strong><br>{0} is now logged in').format(
                user_dict['display_name']
            ),
            allow_html=True
        )

        notice_no_access()

        return h.redirect_to(
            controller='ckanext.canada.controller:CanadaController',
            action='home')
    else:
        err = _(u'Login failed. Bad username or password.')
        h.flash_error(err)
        return h.redirect_to('user.login')


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type, id):
        response = super(CanadaDatasetEditView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                context = self._prepare(id)
                pkg_dict = get_action(u'package_show')(
                    dict(context, for_view=True), {
                        u'id': id
                    }
                )
                if pkg_dict['type'] == 'prop':
                    h.flash_success(_(u'The status has been added / updated for this suggested  dataset. This update will be reflected on open.canada.ca shortly.'))
                else:
                    h.flash_success(_(u'Dataset updated.'))
        return response


class CanadaResourceEditView(ResourceEditView):
    def post(self, package_type, id, resource_id):
        response = super(CanadaResourceEditView, self).post(package_type, id, resource_id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                h.flash_success(_(u'Resource updated.'))
        return response


class CanadaResourceCreateView(ResourceCreateView):
    def post(self, package_type, id):
        response = super(CanadaResourceCreateView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                h.flash_success(_(u'Resource added.'))
        return response


@canada_views.route('/500', methods=['GET'])
def fivehundred():
    raise IntentionalServerError()



def _get_form_full_text_choices(field_name, chromo):
    for field in chromo['fields']:
        if field['datastore_id'] == field_name and \
                field.get('form_full_text_choices', False):
            return True
    return False


@canada_views.route('/create-pd-record/<owner_org>/<resource_name>', methods=['GET', 'POST'])
def create_pd_record(owner_org, resource_name):
    lc = LocalCKAN(username=c.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': c.user, 'auth_user_obj': c.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        return abort(403, _('Unauthorized'))

    choice_fields = {
        f['datastore_id']: [
            {'value': k,
             'label': k + ': ' + v if _get_form_full_text_choices(f['datastore_id'], chromo) else v
             } for (k, v) in f['choices']]
        for f in h.recombinant_choice_fields(resource_name)}

    pk_fields = aslist(chromo['datastore_primary_key'])

    if request.method == 'POST':
        post_data = parse_params(request.form, ignore_keys=['save'])

        if 'cancel' in post_data:
            return h.redirect_to(
                'recombinant.preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
                )

        data, err = _clean_check_type_errors(
            post_data,
            chromo['fields'],
            pk_fields,
            choice_fields)
        try:
            lc.action.datastore_upsert(
                resource_id=res['id'],
                method='insert',
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            if 'records' in ve.error_dict:
                err = dict({
                    k: [_(e) for e in v]
                    for (k, v) in ve.error_dict['records'][0].items()
                }, **err)
            elif ve.error_dict.get('info', {}).get('pgcode', '') == '23505':
                err = dict({
                    k: [_("This record already exists")]
                    for k in pk_fields
                }, **err)

        if err:
            return render('recombinant/create_pd_record.html',
                          extra_vars={
                              'data': data,
                              'resource_name': resource_name,
                              'chromo_title': chromo['title'],
                              'choice_fields': choice_fields,
                              'owner_org': rcomb['owner_org'],
                              'pkg_dict': {},  # prevent rendering error on parent template
                              'errors': err,
                          })

        h.flash_notice(_(u'Record Created'))

        return h.redirect_to(
            'recombinant.preview_table',
            resource_name=resource_name,
            owner_org=rcomb['owner_org'],
        )

    return render('recombinant/create_pd_record.html',
                  extra_vars={
                      'data': {},
                      'resource_name': resource_name,
                      'chromo_title': chromo['title'],
                      'choice_fields': choice_fields,
                      'owner_org': rcomb['owner_org'],
                      'pkg_dict': {},  # prevent rendering error on parent template
                      'errors': {},
                  })


@canada_views.route('/update-pd-record/<owner_org>/<resource_name>/<pk>', methods=['GET', 'POST'])
def update_pd_record(owner_org, resource_name, pk):
    pk = [url_part_unescape(p) for p in pk.split(',')]

    lc = LocalCKAN(username=c.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': c.user, 'auth_user_obj': c.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        abort(403, _('Unauthorized'))

    choice_fields = {
        f['datastore_id']: [
            {'value': k,
             'label': k + ': ' + v if _get_form_full_text_choices(f['datastore_id'], chromo) else v
             } for (k, v) in f['choices']]
        for f in h.recombinant_choice_fields(resource_name)}

    pk_fields = aslist(chromo['datastore_primary_key'])
    pk_filter = dict(zip(pk_fields, pk))

    records = lc.action.datastore_search(
        resource_id=res['id'],
        filters=pk_filter)['records']
    if len(records) == 0:
        abort(404, _('Not found'))
    if len(records) > 1:
        abort(400, _('Multiple records found'))
    record = records[0]

    if request.method == 'POST':
        post_data = parse_params(request.form, ignore_keys=['save'] + pk_fields)

        if 'cancel' in post_data:
            return h.redirect_to(
                'recombinant.preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
                )

        data, err = _clean_check_type_errors(
            post_data,
            chromo['fields'],
            pk_fields,
            choice_fields)
        # can't change pk fields
        for f_id in data:
            if f_id in pk_fields:
                data[f_id] = record[f_id]
        try:
            lc.action.datastore_upsert(
                resource_id=res['id'],
                #method='update',    FIXME not raising ValidationErrors
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            try:
                err = dict({
                    k: [_(e) for e in v]
                    for (k, v) in ve.error_dict['records'][0].items()
                }, **err)
            except AttributeError as e:
                raise ve

        if err:
            return render('recombinant/update_pd_record.html',
                extra_vars={
                    'data': data,
                    'resource_name': resource_name,
                    'chromo_title': chromo['title'],
                    'choice_fields': choice_fields,
                    'pk_fields': pk_fields,
                    'owner_org': rcomb['owner_org'],
                    'pkg_dict': {},  # prevent rendering error on parent template
                    'errors': err,
                    })

        h.flash_notice(_(u'Record %s Updated') % u','.join(pk) )

        return h.redirect_to(
            'recombinant.preview_table',
            resource_name=resource_name,
            owner_org=rcomb['owner_org'],
            )

    data = {}
    for f in chromo['fields']:
        if not f.get('import_template_include', True):
            continue
        val = record[f['datastore_id']]
        data[f['datastore_id']] = val

    return render('recombinant/update_pd_record.html',
        extra_vars={
            'data': data,
            'resource_name': resource_name,
            'chromo_title': chromo['title'],
            'choice_fields': choice_fields,
            'pk_fields': pk_fields,
            'owner_org': rcomb['owner_org'],
            'pkg_dict': {},  # prevent rendering error on parent template
            'errors': {},
            })



@canada_views.route('/recombinant/<resource_name>', methods=['GET'])
def type_redirect(resource_name):
    orgs = h.organizations_available('read')

    if not orgs:
        abort(404, _('No organizations found'))
    try:
        chromo = get_chromo(resource_name)
    except RecombinantException:
        abort(404, _('Recombinant resource_name not found'))

    # custom business logic
    if is_sysadmin(c.user):
        return h.redirect_to(h.url_for('recombinant.preview_table',
                                  resource_name=resource_name, owner_org='tbs-sct'))
    return h.redirect_to(h.url_for('recombinant.preview_table',
                              resource_name=resource_name, owner_org=orgs[0]['name']))

def _clean_check_type_errors(post_data, fields, pk_fields, choice_fields):
    """
    clean posted data and check type errors, add type error messages
    to errors dict returned. This is required because type errors on any
    field prevent triggers from running so we don't get any other errors
    from the datastore_upsert call.
    :param post_data: form data
    :param fields: recombinant fields
    :param pk_fields: list of primary key field ids
    :param choice_fields: {field id: choices, ...}
    :return: cleaned data, errors
    """
    data = {}
    err = {}

    for f in fields:
        f_id = f['datastore_id']
        if not f.get('import_template_include', True):
            continue
        else:
            val = post_data.get(f['datastore_id'], '')
            if isinstance(val, list):
                val = u','.join(val)
            val = canonicalize(
                val,
                f['datastore_type'],
                primary_key=f['datastore_id'] in pk_fields,
                choice_field=f_id in choice_fields)
            if val:
                if f['datastore_type'] in ('money', 'numeric'):
                    try:
                        decimal.Decimal(val)
                    except decimal.InvalidOperation:
                        err[f['datastore_id']] = [_(u'Number required')]
                elif f['datastore_type'] == 'int':
                    try:
                        int(val)
                    except ValueError:
                        err[f['datastore_id']] = [_(u'Integer required')]
            data[f['datastore_id']] = val

    return data, err


def output_feed(results, feed_title, feed_description,
                feed_link, feed_url, navigation_urls, feed_guid):

    author_name = config.get('ckan.feeds.author_name', '').strip() or \
        config.get('ckan.site_id', '').strip()

    feed = CKANFeed(
        feed_title=feed_title,
        feed_link=feed_link,
        feed_description=feed_description,
        language=u'en',
        author_name=author_name,
        feed_guid=feed_guid,
        feed_url=feed_url,
        previous_page=navigation_urls['previous'],
        next_page=navigation_urls['next'],
        first_page=navigation_urls['first'],
        last_page=navigation_urls['last']
    )

    for pkg in results:
        feed.add_item(
            title= h.get_translated(pkg, 'title'),
            link=h.url_for(controller='package', action='read', id=pkg['id']),
            description= h.get_translated(pkg, 'notes'),
            updated=date_str_to_datetime(pkg.get('metadata_modified')),
            published=date_str_to_datetime(pkg.get('metadata_created')),
            unique_id=_create_atom_id(u'/dataset/%s' % pkg['id']),
            author_name=pkg.get('author', ''),
            author_email=pkg.get('author_email', ''),
            categories=''.join(e['value']
                                for e in pkg.get('extras', [])
                                if e['key'] == lx('keywords')).split(','),
            enclosure=webhelpers.feedgenerator.Enclosure(
                BASE_URL + url(str(
                    '/api/action/package_show?id=%s' % pkg['name'])),
                unicode(len(json.dumps(pkg))),   # TODO fix this
                u'application/json'))

    response = make_response(feed.writeString(u'utf-8'), 200)
    response.headers['Content-Type'] = u'application/atom+xml'
    return response


def general_feed():
    data_dict, params = _parse_url_params()
    data_dict['q'] = '*:*'

    item_count, results = _package_search(data_dict)
    # FIXME: url generation for Views
    navigation_urls = _navigation_urls(params,
                                       item_count=item_count,
                                       limit=data_dict['rows'],
                                       controller='canada_feeds',
                                       action='general')
    # FIXME: url generation for Views
    feed_url = _feed_url(params,
                         controller='canada_feeds',
                         action='general')
    # FIXME: url generation for Views
    alternate_url = _alternate_url(params)

    guid = _create_atom_id( u'/feeds/dataset.atom')

    return output_feed(
        results,
        feed_title=_(u'Open Government Dataset Feed'),
        feed_description='',
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def organization_feed(id):
    try:
        context = {'model': model, 'session': model.Session,
                    'user': c.user, 'auth_user_obj': c.userobj}
        org_obj = get_action('organization_show')(context,
                                                  {'id': id})
    except NotFound:
        abort(404, _('Organization not found'))

    data_dict, params = _parse_url_params()

    data_dict['fq'] = u'{0}: "{1}"'.format('owner_org', org_obj['id'])

    item_count, results = _package_search(data_dict)
    # FIXME: url generation for Views
    navigation_urls = _navigation_urls(params,
                                       item_count=item_count,
                                       limit=data_dict['rows'],
                                       controller=u'canada_feeds',
                                       action='organization',
                                       id=org_obj['name'])
    # FIXME: url generation for Views
    feed_url = _feed_url(
        params, controller=u'canada_feeds', action='organization', id=org_obj['name'])
    # FIXME: url generation for Views
    alternate_url = _alternate_url(params, organization=org_obj['name'])

    guid = _create_atom_id(
            u'feeds/organization/%s.atom' % org_obj['name'])

    desc = u'Recently created or updated datasets on %s '\
            'by organization: "%s"' % (SITE_TITLE, org_obj['title'])

    title = u'%s - Organization: "%s"' % (SITE_TITLE, org_obj['title'])

    return output_feed(
        results,
        feed_title=title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def dataset_feed(pkg_id):
    try:
        context = {'model': model, 'session': model.Session,
                    'user': c.user, 'auth_user_obj': c.userobj}
        get_action('package_show')(context,
                                   {'id': pkg_id})
    except NotFound:
        abort(404, _('Dataset not found'))

    data_dict, params = _parse_url_params()

    data_dict['fq'] = '{0}:"{1}"'.format('id', pkg_id)

    item_count, results = _package_search(data_dict)
    # FIXME: url generation for Views
    navigation_urls = _navigation_urls(params,
                                       item_count=item_count,
                                       limit=data_dict['rows'],
                                       controller='canada_feeds',
                                       action='dataset',
                                       id=pkg_id)
    # FIXME: url generation for Views
    feed_url = _feed_url(params,
                         controller='canada_feeds',
                         action='dataset',
                         id=pkg_id)
    # FIXME: url generation for Views
    alternate_url = _alternate_url(params,
                                   id=pkg_id)

    guid = _create_atom_id(u'/feeds/dataset/{0}.atom'.format(pkg_id))

    return output_feed(
        results,
        feed_title=_(u'Open Government Dataset Feed'),
        feed_description='',
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


# Routing
canada_views.add_url_rule(u'/logged_in', view_func=logged_in)
canada_feeds.add_url_rule(u'/dataset/<string:pkg_id>.atom', methods=[u'GET'], view_func=dataset_feed)
canada_feeds.add_url_rule(u'/organization/<string:id>.atom', methods=[u'GET'], view_func=organization_feed)
canada_feeds.add_url_rule(u'/general.atom', methods=[u'GET'], view_func=general_feed)

