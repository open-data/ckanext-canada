import json
import decimal
from pytz import timezone, utc
from socket import error as socket_error
from logging import getLogger
import csv
from six import string_types
from datetime import datetime, timedelta

from ckan.config.middleware.flask_app import csrf

from ckan.plugins.toolkit import (
    abort,
    get_action,
    _,
    h,
    g,
    config,
    check_access,
    aslist,
    request,
    render
)
import ckan.lib.mailer as mailer
from ckan import model
from ckan.lib.helpers import (
    date_str_to_datetime,
    lang
)

from ckan.views.dataset import (
    EditView as DatasetEditView,
    search as dataset_search,
    CreateView as DatasetCreateView,
)
from ckanext.activity.views import package_activity
from ckan.views.resource import (
    EditView as ResourceEditView,
    CreateView as ResourceCreateView
)
from ckan.views.user import RegisterView as UserRegisterView
from ckan.views.api import(
    API_DEFAULT_VERSION,
    API_MAX_VERSION,
    _finish_ok,
    _finish,
    action as api_view_action,
    _get_request_data
)
from ckan.views.group import set_org
from ckan.views.admin import _get_sysadmins

from ckan.authz import is_sysadmin
from ckan.logic import (
    parse_params,
    ValidationError,
    NotFound,
    NotAuthorized
)

from ckanext.recombinant.datatypes import canonicalize
from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.errors import RecombinantException

from ckanapi import LocalCKAN

from flask import Blueprint, make_response

from ckanext.canada.urlsafe import url_part_unescape, url_part_escape
from ckanext.canada.helpers import canada_date_str_to_datetime

from io import StringIO

BOM = "\N{bom}"

from logging import getLogger

log = getLogger(__name__)

MAX_JOB_QUEUE_LIST_SIZE = 25

canada_views = Blueprint('canada', __name__)
ottawa_tz = timezone('America/Montreal')


class IntentionalServerError(Exception):
    pass


@canada_views.route('/user/logged_in', methods=['GET'])
def logged_in():
    # redirect if needed
    came_from = request.args.get(u'came_from', u'')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))

    if g.user:
        user_dict = get_action('user_show')(None, {'id': g.user})

        h.flash_success(
            _('<strong>Note</strong><br>{0} is now logged in').format(
                user_dict['display_name']
            ),
            allow_html=True
        )

        notice_no_access()

        return h.redirect_to('canada.home')
    else:
        err = _(u'Login failed. Bad username or password.')
        h.flash_error(err)
        return h.redirect_to('user.login')


def _get_package_type_from_dict(package_id, package_type='dataset'):
    try:
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        pkg_dict = get_action(u'package_show')(
            dict(context, for_view=True), {
                u'id': package_id
            }
        )
        return pkg_dict['type']
    except (NotAuthorized, NotFound):
        return package_type


def canada_prevent_pd_views(uri, package_type):
    uri = uri.split('/')
    id = None
    if uri[0]:
        if uri[0] == 'activity':  # allow activity route
            return package_activity(package_type, uri[1])
        id = uri[0]
        package_type = _get_package_type_from_dict(id, package_type)
    if package_type in h.recombinant_get_types():
        return type_redirect(package_type, id)
    return abort(404)


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type, id):
        response = super(CanadaDatasetEditView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                context = self._prepare()
                pkg_dict = get_action(u'package_show')(
                    dict(context, for_view=True), {
                        u'id': id
                    }
                )
                if pkg_dict['type'] == 'prop':
                    h.flash_success(_(u'The status has been added/updated for this suggested dataset. This update will be reflected on open.canada.ca shortly.'))
                else:
                    h.flash_success(
                        _("Your dataset %s has been saved.")
                        % pkg_dict['id'])
        return response


class CanadaDatasetCreateView(DatasetCreateView):
    def post(self, package_type):
        response = super(CanadaDatasetCreateView, self).post(package_type)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                h.flash_success(_(u'Dataset added.'))
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


class CanadaUserRegisterView(UserRegisterView):
    def post(self):
        params = parse_params(request.form)
        email=params.get('email', '')
        fullname=params.get('fullname', '')
        username=params.get('name', '')
        phoneno=params.get('phoneno', '')
        dept=params.get('department', '')
        response = super(CanadaUserRegisterView, self).post()
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                if not config.get('ckanext.canada.suppress_user_emails', False):
                    # redirected after successful user create
                    import ckan.lib.mailer
                    # checks if there is a custom function "notify_ckan_user_create" in the mailer (added by ckanext-gcnotify)
                    getattr(
                        ckan.lib.mailer,
                        "notify_ckan_user_create",
                        notify_ckan_user_create
                    )(
                        email=email,
                        fullname=fullname,
                        username=username,
                        phoneno=phoneno,
                        dept=dept)
                notice_no_access()
        return response


canada_views.add_url_rule(
    u'/user/register',
    view_func=CanadaUserRegisterView.as_view(str(u'register'))
)


@canada_views.route('/recover-username', methods=['GET', 'POST'])
def recover_username():
    if not g.is_registry or not h.plugin_loaded('gcnotify'):
        # we only want this route on the Registry, and the email template
        # is monkey patched in GC Notify so we need that loaded
        return abort(404)

    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    try:
        check_access('request_reset', context)
    except NotAuthorized:
        abort(403, _('Unauthorized to request username recovery.'))

    if request.method == 'POST':
        email = request.form.get('email')
        if email in (None, ''):
            h.flash_error(_('Email is required'))
            return h.redirect_to('canada.recover_username')

        log.info('Username recovery requested for email "{}"'.format(email))

        context = {'model': model, 'user': g.user, 'ignore_auth': True}
        username_list = []

        user_list = get_action('user_list')(context, {'email': email})
        if user_list:
            for user_dict in user_list:
                username_list.append(user_dict['name'])

        if not username_list:
            log.info('User requested username recovery for unknown email: {}'
                     .format(email))
        else:
            log.info('Emailing username recovery to email: {}'
                     .format(email))
            try:
                # see: ckanext.gcnotify.mailer.send_username_recovery
                mailer.send_username_recovery(email, username_list)
            except mailer.MailerException as e:
                # SMTP is not configured correctly or the server is
                # temporarily unavailable
                h.flash_error(_('Error sending the email. Try again later '
                                'or contact an administrator for help'))
                log.exception(e)
                return h.redirect_to('home.index')

        # always tell the user it succeeded, because otherwise we reveal
        # which accounts exist or not
        h.flash_success(_('An email has been sent to you containing '
                          'your username(s). (unless the account specified'
                          ' does not exist)'))
        return h.redirect_to('home.index')

    return render('user/recover_username.html', {})


def canada_search(package_type):
    if g.is_registry and not g.user:
        return abort(403)
    if not g.is_registry and package_type in h.recombinant_get_types():
        return h.redirect_to('dataset.search', package_type='dataset')
    return dataset_search(package_type)


@canada_views.route('/500', methods=['GET'])
def fivehundred():
    raise IntentionalServerError()


def _form_choices_prefix_code(field_name, chromo):
    for field in chromo['fields']:
        if field['datastore_id'] == field_name and \
                field.get('form_choices_prefix_code', False):
            return True
    return False


def _get_choice_fields(resource_name, chromo):
    separator = ' : ' if h.lang() == 'fr' else ': '
    return {
        datastore_id: [
            {'value': k,
             'label': k + separator + v if _form_choices_prefix_code(datastore_id, chromo) else v
             } for (k, v) in choices]
        for datastore_id, choices in h.recombinant_choice_fields(resource_name).items()}


@canada_views.route('/group/bulk_process/<id>', methods=['GET', 'POST'])
def canada_group_bulk_process(id, group_type='group', is_organization=False, data=None):
    """
    Redirects the Group bulk action endpoint as it does not support
    the IPackageController and IResourceController implementations.
    """
    return h.redirect_to('%s.read' % group_type, id=id)


@canada_views.route('/organization/bulk_process/<id>', methods=['GET', 'POST'])
def canada_organization_bulk_process(id, group_type='organization', is_organization=True, data=None):
    """
    Redirects the Organization bulk action endpoint as it does not support
    the IPackageController and IResourceController implementations.
    """
    return h.redirect_to('%s.read' % group_type, id=id)


@canada_views.route('/create-pd-record/<owner_org>/<resource_name>', methods=['GET', 'POST'])
def create_pd_record(owner_org, resource_name):
    lc = LocalCKAN(username=g.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': g.user, 'auth_user_obj': g.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        return abort(403, _('Unauthorized to create a resource for this package'))

    choice_fields = _get_choice_fields(resource_name, chromo)
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
        error_summary = None
        try:
            lc.action.datastore_upsert(
                resource_id=res['id'],
                method='insert',
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            if 'records' in ve.error_dict:
                try:
                    err = dict({
                        k: [_(e) for e in v]
                        for (k, v) in ve.error_dict['records'][0].items()
                    }, **err)
                except AttributeError:
                    if 'duplicate key value violates unique constraint' in ve.error_dict['records'][0]:
                        err = dict({
                            k: [_("This record already exists")]
                            for k in pk_fields
                        }, **err)
                    else:
                        error_summary = _('Something went wrong, your record was not created. Please contact support.')
            elif ve.error_dict.get('info', {}).get('pgcode', '') == '23505':
                err = dict({
                    k: [_("This record already exists")]
                    for k in pk_fields
                }, **err)
            else:
                error_summary = _('Something went wrong, your record was not created. Please contact support.')

        if err or error_summary:
            return render('recombinant/create_pd_record.html',
                          extra_vars={
                              'data': data,
                              'resource_name': resource_name,
                              'chromo_title': chromo['title'],
                              'choice_fields': choice_fields,
                              'owner_org': rcomb['owner_org'],
                              'pkg_dict': {},  # prevent rendering error on parent template
                              'errors': err,
                              'error_summary': error_summary,
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

    lc = LocalCKAN(username=g.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': g.user, 'auth_user_obj': g.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        abort(403, _('Unauthorized to update dataset'))

    choice_fields = _get_choice_fields(resource_name, chromo)
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
        error_summary = None
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
            except AttributeError:
                error_summary = _('Something went wrong, your record was not updated. Please contact support.')

        if err or error_summary:
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
                    'error_summary': error_summary,
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
        if f.get('datastore_type') == 'money':
            if isinstance(val, str) and '$' in val:
                data[f['datastore_id']] = val
            else:
                data[f['datastore_id']] = '${:,.2f}'.format(val)
        else:
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
def type_redirect(resource_name, dataset_id=None):
    orgs = h.organizations_available('read')

    if not orgs:
        abort(404, _('No organizations found'))
    try:
        chromo = get_chromo(resource_name)
    except RecombinantException:
        abort(404, _('Recombinant resource_name not found'))

    if is_sysadmin(g.user):
        # if sysadmin, always go to tbs-sct
        owner_org_name = 'tbs-sct'
    else:
        # otherwise, go to first org in user's available list
        owner_org_name = orgs[0]['name']

    if dataset_id:
        try:
            dataset = get_action('package_show')({'user': g.user}, {'id': dataset_id})
        except NotAuthorized:
            return abort(403)
        except NotFound:
            return abort(404)

        if dataset.get('owner_org'):
            org_obj = model.Group.get(dataset.get('owner_org'))
            if org_obj:
                owner_org_name = org_obj.name

    return h.redirect_to(h.url_for('recombinant.preview_table',
                                   resource_name=resource_name,
                                   owner_org=owner_org_name))


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


@canada_views.route('/', methods=['GET'])
def home():
    if not g.is_registry:
        return h.redirect_to('dataset.search')
    if not g.user:
        return h.redirect_to('user.login')

    is_new = not h.check_access('package_create')

    if is_new:
        return h.redirect_to('dataset.search')

    return h.redirect_to('canada.links')


@canada_views.route('/links', methods=['GET'])
def links():
    if not g.is_registry:
        return h.redirect_to('dataset.search')
    return render('home/quick_links.html', extra_vars={'is_sysadmin': is_sysadmin(g.user)})


@canada_views.route('/ckan-admin/publish', methods=['GET', 'POST'])
def ckanadmin_publish():
    """
    Executes a dataset_search for the route.
    See: ckanext/canada/plugins.py:CanadaDatasetsPlugin.before_search
    for custom search facets for this admin route.
    """
    if not is_sysadmin(g.user):
        abort(403, _('Not authorized to see this page'))

    return dataset_search('dataset')


@canada_views.route('/ckan-admin/publish-datasets', methods=['GET', 'POST'])
def ckanadmin_publish_datasets():
    if not is_sysadmin(g.user):
        abort(403, _('Not authorized to see this page'))

    lc = LocalCKAN(username=g.user)
    params = parse_params(request.form)

    publish_date = params.get('publish_date')
    publish_date = date_str_to_datetime(publish_date).strftime("%Y-%m-%d %H:%M:%S")

    # get a list of package id's from the for POST data
    publish_packages = params.get('publish', [])
    if isinstance(publish_packages, string_types):
        publish_packages = [publish_packages]
    count = len(publish_packages)
    for package_id in publish_packages:
        lc.action.package_patch(
            id=package_id,
            portal_release_date=publish_date,
        )

    # flash notice that records are published
    h.flash_notice(str(count) + _(u' record(s) published.'))

    # return us to the publishing interface
    return h.redirect_to('canada.ckanadmin_publish')


@canada_views.route('/ckan-admin/job-queue', methods=['GET'])
def ckanadmin_job_queue():
    """
    Lists all of the queued and running jobs.
    """
    try:
        jobs = get_action('job_list')({}, {'limit': MAX_JOB_QUEUE_LIST_SIZE})
    except NotAuthorized:
        abort(403, _('Not authorized to see this page'))

    warning = False
    if jobs and datetime.strptime(jobs[0]['created'], '%Y-%m-%dT%H:%M:%S') < (datetime.now() - timedelta(minutes=18)):
        warning = True

    return render('admin/jobs.html', extra_vars={'job_list': jobs,
                                                 'warning': warning,})


@canada_views.route('/help', methods=['GET'])
def view_help():
    if not g.is_registry:
        return abort(404)
    return render('help.html', extra_vars={})


@canada_views.route('/datatable/<resource_name>/<resource_id>', methods=['GET', 'POST'])
@csrf.exempt
def datatable(resource_name, resource_id):
    params = parse_params(request.form)
    draw = int(params['draw'])
    search_text = str(params['search[value]'])
    offset = int(params['start'])
    limit = int(params['length'])

    chromo = h.recombinant_get_chromo(resource_name)
    lc = LocalCKAN(username=g.user)
    try:
        unfiltered_response = lc.action.datastore_search(
            resource_id=resource_id,
            limit=1,
        )
    except NotAuthorized:
        # datatables js can't handle any sort of error response
        # return no records instead
        return json.dumps({
            'draw': draw,
            'iTotalRecords': -1,  # with a hint that something is wrong
            'iTotalDisplayRecords': -1,
            'aaData': [],
        })

    can_edit = h.check_access('resource_update', {'id': resource_id})
    cols = [f['datastore_id'] for f in chromo['fields']]
    prefix_cols = 2 if chromo.get('edit_form', False) and can_edit else 1  # Select | (Edit) | ...

    sort_list = []
    i = 0
    while True:
        if u'order[%d][column]' % i not in params:
            break
        sort_by_num = int(params[u'order[%d][column]' % i])
        sort_order = (
            u'desc' if params[u'order[%d][dir]' % i] == u'desc'
            else u'asc')
        sort_list.append(cols[sort_by_num - prefix_cols] + u' ' + sort_order + u' nulls last')
        i += 1

    response = lc.action.datastore_search(
        q=search_text,
        resource_id=resource_id,
        offset=offset,
        limit=limit,
        sort=u', '.join(sort_list),
    )

    aadata = [
        [u'<input type="checkbox">'] +
        [datatablify(row.get(colname, u''), colname, chromo) for colname in cols]
        for row in response['records']]

    if chromo.get('edit_form', False) and can_edit:
        res = lc.action.resource_show(id=resource_id)
        pkg = lc.action.package_show(id=res['package_id'])
        fids = [f['datastore_id'] for f in chromo['fields']]
        pkids = [fids.index(k) for k in aslist(chromo['datastore_primary_key'])]
        for row in aadata:
            row.insert(1, (
                    u'<a href="{0}" aria-label="' + _("Edit") + '">'
                    u'<i class="fa fa-lg fa-edit" aria-hidden="true"></i></a>').format(
                    h.url_for(
                        'canada.update_pd_record',
                        owner_org=pkg['organization']['name'],
                        resource_name=resource_name,
                        pk=','.join(url_part_escape(row[i+1]) for i in pkids)
                    )
                )
            )

    return json.dumps({
        'draw': draw,
        'iTotalRecords': unfiltered_response.get('total', 0),
        'iTotalDisplayRecords': response.get('total', 0),
        'aaData': aadata,
    })


def datatablify(v, colname, chromo):
    '''
    format value from datastore v for display in a datatable preview
    '''
    chromo_field = None
    for f in chromo['fields']:
        if f['datastore_id'] == colname:
            chromo_field = f
            break
    if v is None:
        return u''
    if v is True:
        return u'TRUE'
    if v is False:
        return u'FALSE'
    if isinstance(v, list):
        return u', '.join(str(e) for e in v)
    if colname in ('record_created', 'record_modified') and v:
        return canada_date_str_to_datetime(v).replace(tzinfo=utc).astimezone(
            ottawa_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    if chromo_field and chromo_field.get('datastore_type') == 'money':
        if isinstance(v, str) and '$' in v:
            return v
        return '${:,.2f}'.format(v)
    return str(v)


@canada_views.route('/fgpv-vpgf/<pkg_id>', methods=['GET'])
def fgpv_vpgf(pkg_id):
    return render('fgpv_vpgf/index.html', extra_vars={
        'pkg_id': pkg_id,
    })


@canada_views.route('/organization/autocomplete', methods=['GET'])
def organization_autocomplete():
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20)
    organization_list = []

    if q:
        context = {'user': g.user, 'model': model, 'ignore_auth': True}
        data_dict = {'q': q, 'limit': limit}
        organization_list = get_action(
            'organization_autocomplete'
        )(context, data_dict)

    def _org_key(org):
        return org['title'].split(' | ')[-1 if lang() == 'fr' else 0]

    return_list = [{
        'id': o['id'],
        'name': _org_key(o),
        'title': _org_key(o)
    } for o in organization_list]

    return _finish_ok(return_list)


@canada_views.route('/api/<int(min=1, max=2):ver>/action/<logic_function>', methods=['GET', 'POST'])
@canada_views.route('/api/action/<logic_function>', methods=[u'GET', u'POST'])
@canada_views.route('/api/<int(min=3, max={0}):ver>/action/<logic_function>'.format(
                    API_MAX_VERSION), methods=[u'GET', u'POST'])
def action(logic_function, ver=API_DEFAULT_VERSION):
    u'''Main endpoint for the action API (v3)

    Creates a dict with the incoming request data and calls the appropiate
    logic function. Returns a JSON response with the following keys:

        * ``help``: A URL to the docstring for the specified action
        * ``success``: A boolean indicating if the request was successful or
                an exception was raised
        * ``result``: The output of the action, generally an Object or an Array

    Canada Fork:
        We keep version 1 and 2 endpoints just incase any systems are still using that.
        We also have -1 to version to return the context and request_data for extra logging.
        And if the request is a POST request, we want to not authorize any PD type.
    '''
    try:
        function = get_action(logic_function)
    except Exception:
        return api_view_action(logic_function, ver)

    try:
        side_effect_free = getattr(function, u'side_effect_free', False)
        request_data = _get_request_data(try_url_params=side_effect_free)
    except Exception:
        return api_view_action(logic_function, ver)

    if not isinstance(request_data, dict):
        return api_view_action(logic_function, ver)

    context = {u'model': model, u'session': model.Session, u'user': g.user,
               u'api_version': ver, u'auth_user_obj': g.userobj}

    return_dict = {u'help': h.url_for(u'api.action',
                                      logic_function=u'help_show',
                                      ver=ver,
                                      name=logic_function,
                                      _external=True,)}

    # extra logging here
    id = request_data.get('id', request_data.get('package_id', request_data.get('resource_id')))
    pkg_dict = _get_package_from_api_request(logic_function, id, context)
    if pkg_dict:
        _log_api_access(request_data, pkg_dict)

    # prevent PD types from being POSTed to via the API, but allow DataStore POSTing
    if request.method == 'POST' and not logic_function.startswith('datastore'):
        package_type = pkg_dict.get('type') if pkg_dict \
            else request_data.get('package_type', request_data.get('type'))
        if package_type and package_type in h.recombinant_get_types():
            return_dict[u'error'] = {u'__type': u'Authorization Error',
                                    u'message': _(u'Access denied')}
            return_dict[u'success'] = False

            return _finish(403, return_dict, content_type=u'json')

    return api_view_action(logic_function, ver)


def _get_package_from_api_request(logic_function, id, context):
    # type: (str, str, dict) -> dict|None
    """
    Tries to return the package for an API request
    """
    if not id:
        return None
    if logic_function.startswith('group') \
    or logic_function.startswith('organization') \
    or logic_function.startswith('urser'):
        return None
    if logic_function.startswith('resource') \
    or logic_function.startswith('datastore'):
        try:
            res_dict = get_action(u'resource_show')(context, {u'id': id})
            id = res_dict['package_id']
        except (NotAuthorized, NotFound):
            pass
    try:
        pkg_dict = get_action(u'package_show')(context, {u'id': id})
        return pkg_dict
    except (NotAuthorized, NotFound):
        return None


def _log_api_access(request_data, pkg_dict):
    org = model.Group.get(pkg_dict.get('owner_org'))
    g.log_extra = u'org={o} type={t} id={i}'.format(
        o=org.name,
        t=pkg_dict.get('type'),
        i=pkg_dict.get('id'))
    if 'resource_id' in request_data:
        g.log_extra += u' rid={0}'.format(request_data['resource_id'])


def notice_no_access():
    '''flash_notice if logged-in user can't actually do anything yet.'''
    if get_action('organization_list_for_user')({'user': g.user},
                                                {'permission': 'read',
                                                 'include_dataset_count': False}):
        return

    h.flash_notice(
        '<strong>' + _('Account Created') +
        '</strong><br>' +
        _('Thank you for creating your account for the Open '
          'Government registry. Although your account is active, '
          'it has not yet been linked to your department. Until '
          'the account is linked to your department you will not '
          'be able to create or modify datasets in the '
          'registry.') +
        '<br><br>' +
        _('You should receive an email within the next business '
          'day once the account activation process has been '
          'completed. If you require faster processing of the '
          'account, please send the request directly to: '
          '<a href="mailto:open-ouvert@tbs-sct.gc.ca">'
          'open-ouvert@tbs-sct.gc.ca</a>'), True)


def notify_ckan_user_create(email, fullname, username, phoneno, dept):
    """
    Send an e-mail notification about new users that register on the site to
    the configured recipient and to the new user
    """
    import ckan.lib.mailer

    try:
        if 'canada.notification_new_user_email' in config:
            xtra_vars = {
                'email': email,
                'fullname': fullname,
                'username': username,
                'phoneno': phoneno,
                'dept': dept
            }
            ckan.lib.mailer.mail_recipient(
                config.get(
                    'canada.notification_new_user_name',
                    config['canada.notification_new_user_email']
                ),
                config['canada.notification_new_user_email'],
                (
                    u'New Registry Account Created / Nouveau compte'
                    u' cr\u00e9\u00e9 dans le registre de Gouvernement ouvert'
                ),
                render(
                    'user/new_user_email.html',
                    extra_vars=xtra_vars
                )
            )
    except ckan.lib.mailer.MailerException as m:
        log = getLogger('ckanext')
        log.error(m.message)

    try:
        xtra_vars = {
            'email': email,
            'fullname': fullname,
            'username': username,
            'phoneno': phoneno,
            'dept': dept
        }
        ckan.lib.mailer.mail_recipient(
            fullname or email,
            email,
            (
                u'Welcome to the Open Government Registry / '
                u'Bienvenue au Registre de Gouvernement Ouvert'
            ),
            render(
                'user/user_welcome_email.html',
                extra_vars=xtra_vars
            )
        )
    except (ckan.lib.mailer.MailerException, socket_error) as m:
        log = getLogger('ckanext')
        log.error(m.message)


@canada_views.route('/organization/member_dump/<id>', methods=['GET'])
def organization_member_dump(id):
    records_format = u'csv'

    org_dict = model.Group.get(id)
    if not org_dict:
        abort(404, _(u'Organization not found'))

    context = {u'model': model,
                u'session': model.Session,
                u'user': g.user}

    try:
        check_access('organization_member_create', context, {u'id': id})
    except NotAuthorized:
        abort(404,
             _(u'Not authorized to access {org_name} members download'
                .format(org_name=org_dict.title)))

    try:
        members = get_action(u'member_list')(context, {
            u'id': id,
            u'object_type': u'user',
            u'records_format': records_format,
            u'include_total': False,
        })
    except NotFound:
        abort(404, _('Members not found'))

    results = [[_('Username'), _('Email'), _('Name'), _('Role')]]
    for uid, _user, role in members:
        user_obj = model.User.get(uid)
        if not user_obj:
            continue
        results.append([
            user_obj.name,
            user_obj.email,
            user_obj.fullname if user_obj.fullname else _('N/A'),
            role,
        ])

    output_stream = StringIO()
    output_stream.write(BOM)
    csv.writer(output_stream).writerows(results)

    file_name = u'{org_id}-{members}'.format(
            org_id=org_dict.name,
            members=_(u'members'))

    output_stream.seek(0)
    response = make_response(output_stream.read())
    output_stream.close()
    content_disposition = u'attachment; filename="{name}.csv"'.format(
                                    name=file_name)
    content_type = b'text/csv; charset=utf-8'
    response.headers['Content-Type'] = content_type
    response.headers['Content-Disposition'] = content_disposition

    return response


@canada_views.route('/organization/members/<id>', methods=['GET', 'POST'])
def members(id):
    """
    Copied from core. Permissions for Editors to view members in GET.
    """
    extra_vars = {}
    set_org(True)
    context = {u'model': model, u'session': model.Session, u'user': g.user}

    try:
        data_dict = {u'id': id}
        if request.method == 'POST':
            auth_action = u'group_edit_permissions'
        else:
            auth_action = u'view_org_members'
        check_access(auth_action, context, data_dict)
        members = get_action(u'member_list')(context, {
            u'id': id,
            u'object_type': u'user'
        })
        data_dict['include_datasets'] = False
        group_dict = get_action(u'organization_show')(context, data_dict)
    except NotFound:
        abort(404, _(u'Organization not found'))
    except NotAuthorized:
        if request.method == 'POST':
            error_message = _(u'User %r not authorized to edit members of %s') % (g.user, id)
        else:
            error_message = _(u'User %r not authorized to view members of %s') % (g.user, id)
        abort(403, error_message)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.members = members
    g.group_dict = group_dict

    extra_vars = {
        u"members": members,
        u"group_dict": group_dict,
        u"group_type": 'organization'
    }
    return render(u'organization/members.html', extra_vars)


@canada_views.route('/ckan-admin', methods=['GET'], strict_slashes=False)
def ckan_admin_index():
    """
    Overrides core Admin Index view, to exclude the site user.
    """
    try:
        check_access('sysadmin', {'user': g.user})
    except NotAuthorized:
        abort(403)
    site_id = config.get('ckan.site_id')
    sysadmins = []
    for admin in _get_sysadmins():
        if admin.name == site_id:
            continue
        sysadmins.append(admin.name)
    return render(u'admin/index.html', extra_vars={'sysadmins': sysadmins})


@canada_views.route('/ckan-admin/config', methods=['GET', 'POST'])
def ckan_admin_config():
    """
    404 this page always.
    """
    return abort(404)
