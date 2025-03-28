import re
import codecs
import json
import decimal
from pytz import timezone, utc
from socket import error as socket_error
from logging import getLogger
import csv
from six import string_types
from datetime import datetime, timedelta
import traceback
from functools import partial

from typing import Optional, Union, Any, cast, Dict, List, Tuple
from ckan.types import Context, Response

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
    lang,
    Page,
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
from ckan.views.api import (
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
    tuplize_dict,
    clean_dict,
    ValidationError,
    NotFound,
    NotAuthorized
)
from ckan.lib.navl.dictization_functions import unflatten

from ckanext.recombinant.datatypes import canonicalize
from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.errors import RecombinantException, format_trigger_error
from ckanext.recombinant.helpers import recombinant_primary_key_fields
from ckanext.recombinant.views import _render_recombinant_constraint_errors

from ckanapi import LocalCKAN

from flask import Blueprint, make_response

from ckanext.canada.helpers import canada_date_str_to_datetime

from io import StringIO


BOM = "\N{bom}"
MAX_JOB_QUEUE_LIST_SIZE = 25


log = getLogger(__name__)

canada_views = Blueprint('canada', __name__)
ottawa_tz = timezone('America/Montreal')


class IntentionalServerError(Exception):
    pass


def _url_part_escape(orig: str) -> str:
    """
    simple encoding for url-parts where all non-alphanumerics are
    wrapped in e.g. _xxyyzz_ blocks w/hex UTF-8 xx, yy, zz values

    used for safely including arbitrary unicode as part of a url path
    all returned characters will be in [a-zA-Z0-9_-]
    """
    return '_'.join(
        codecs.encode(s.encode('utf-8'), 'hex').decode('ascii') if i % 2 else s
        for i, s in enumerate(
            re.split(r'([^-a-zA-Z0-9]+)', orig)
        )
    )


def _url_part_unescape(urlpart: str) -> str:
    """
    reverse url_part_escape
    """
    return ''.join(
        codecs.decode(s, 'hex').decode('utf-8') if i % 2 else s
        for i, s in enumerate(urlpart.split('_'))
    )


@canada_views.route('/user/logged_in', methods=['GET'])
def logged_in():
    # redirect if needed
    came_from = request.args.get('came_from', '')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))

    if g.user:
        user_dict = get_action('user_show')(cast(Context, {}), {'id': g.user})

        h.flash_success(
            _('<strong>Note</strong><br>{0} is now logged in').format(
                user_dict['display_name']
            ),
            allow_html=True
        )

        notice_no_access()

        return h.redirect_to('canada.home')
    else:
        err = _('Login failed. Bad username or password.')
        h.flash_error(err)
        return h.redirect_to('user.login')


def _get_package_type_from_dict(package_id: str,
                                package_type:
                                    Optional[Union[str, Any]] = 'dataset') -> str:
    try:
        context = cast(Context, {'model': model,
                                 'session': model.Session,
                                 'user': g.user,
                                 'auth_user_obj': g.userobj,
                                 'for_view': True})
        pkg_dict = get_action('package_show')(context, {'id': package_id})
        return pkg_dict['type']
    except (NotAuthorized, NotFound):
        return package_type  # type: ignore


def canada_prevent_pd_views(uri: str, package_type: str) -> Union[Response, str]:
    uri_parts = uri.split('/')
    id = None
    if uri_parts[0]:
        if uri_parts[0] == 'activity':  # allow activity route
            return package_activity(package_type)
        id = uri_parts[0]
        package_type = _get_package_type_from_dict(id, package_type)
    if package_type in h.recombinant_get_types():
        return type_redirect(package_type, id)
    return abort(404)


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type: str, id: str):
        response = super(CanadaDatasetEditView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            # type_ignore_reason: checking attribute
            if (
              response.status_code == 200 or  # type: ignore
              response.status_code == 302):  # type: ignore
                context = self._prepare()
                pkg_dict = get_action('package_show')(
                    cast(Context, dict(context, for_view=True)), {
                        'id': id
                    }
                )
                if pkg_dict['type'] == 'prop':
                    h.flash_success(_('The status has been added/updated for this '
                                      'suggested dataset. This update will be '
                                      'reflected on open.canada.ca shortly.'))
                else:
                    h.flash_success(
                        _("Your dataset %s has been saved.")
                        % pkg_dict['id'])
        return response


class CanadaDatasetCreateView(DatasetCreateView):
    def post(self, package_type: str):
        response = super(CanadaDatasetCreateView, self).post(package_type)
        if hasattr(response, 'status_code'):
            # type_ignore_reason: checking attribute
            if (
              response.status_code == 200 or  # type: ignore
              response.status_code == 302):  # type: ignore
                h.flash_success(_('Dataset added.'))
        return response


class CanadaResourceEditView(ResourceEditView):
    def post(self, package_type: str, id: str, resource_id: str):
        response = super(CanadaResourceEditView, self).post(
            package_type, id, resource_id)
        if hasattr(response, 'status_code'):
            # type_ignore_reason: checking attribute
            if (
              response.status_code == 200 or  # type: ignore
              response.status_code == 302):  # type: ignore
                h.flash_success(_('Resource updated.'))
        return response


class CanadaResourceCreateView(ResourceCreateView):
    def post(self, package_type: str, id: str):
        response = super(CanadaResourceCreateView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            # type_ignore_reason: checking attribute
            if (
              response.status_code == 200 or  # type: ignore
              response.status_code == 302):  # type: ignore
                h.flash_success(_('Resource added.'))
        return response


class CanadaUserRegisterView(UserRegisterView):
    def post(self):
        data = clean_dict(unflatten(tuplize_dict(parse_params(request.form))))
        email = data.get('email', '')
        fullname = data.get('fullname', '')
        username = data.get('name', '')
        phoneno = data.get('phoneno', '')
        dept = data.get('department', '')
        response = super(CanadaUserRegisterView, self).post()
        if hasattr(response, 'status_code'):
            # type_ignore_reason: checking attribute
            if (
              response.status_code == 200 or  # type: ignore
              response.status_code == 302):  # type: ignore
                if not config.get('ckanext.canada.suppress_user_emails', False):
                    # redirected after successful user create
                    import ckan.lib.mailer
                    # checks if there is a custom function "notify_ckan_user_create"
                    # in the mailer (added by ckanext-gcnotify)
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
    '/user/register',
    view_func=CanadaUserRegisterView.as_view(str('register'))
)


@canada_views.route('/recover-username', methods=['GET', 'POST'])
def recover_username():
    if not g.is_registry or not h.plugin_loaded('gcnotify'):
        # we only want this route on the Registry, and the email template
        # is monkey patched in GC Notify so we need that loaded
        return abort(404)

    context = cast(Context, {'model': model,
                             'session': model.Session,
                             'user': g.user,
                             'auth_user_obj': g.userobj})
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

        context = cast(Context, {'model': model, 'user': g.user, 'ignore_auth': True})
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
                if hasattr(mailer, 'send_username_recovery'):
                    # type_ignore_reason: checking attribute
                    mailer.send_username_recovery(email, username_list)  # type: ignore
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


def canada_search(package_type: str):
    if g.is_registry and not g.user:
        return abort(403)
    if not g.is_registry and package_type in h.recombinant_get_types():
        return h.redirect_to('dataset.search', package_type='dataset')
    return dataset_search(package_type)


@canada_views.route('/500', methods=['GET'])
def fivehundred():
    raise IntentionalServerError()


def _get_choice_fields(resource_name: str) -> Dict[str, Any]:
    separator = ' : ' if h.lang() == 'fr' else ': '
    choice_fields = {}
    for datastore_id, choices in h.recombinant_choice_fields(resource_name).items():
        f = h.recombinant_get_field(resource_name, datastore_id)
        form_choices_prefix_code = f.get('form_choices_prefix_code', False)
        form_choice_keys_only = f.get('form_choice_keys_only', False)
        if datastore_id not in choice_fields:
            choice_fields[datastore_id] = []
        for (k, v) in choices:
            if form_choice_keys_only:
                choice_fields[datastore_id].append({'value': k,
                                                    'label': k})
                continue
            elif form_choices_prefix_code:
                choice_fields[datastore_id].append({'value': k,
                                                    'label': k + separator + v})
                continue
            choice_fields[datastore_id].append({'value': k,
                                                'label': v})
    return choice_fields


@canada_views.route('/group/bulk_process/<id>', methods=['GET', 'POST'])
def canada_group_bulk_process(id: str, group_type: str = 'group',
                              is_organization: Optional[bool] = False,
                              data: Optional[Dict[str, Any]] = None):
    """
    Redirects the Group bulk action endpoint as it does not support
    the IPackageController and IResourceController implementations.
    """
    return h.redirect_to('%s.read' % group_type, id=id)


@canada_views.route('/organization/bulk_process/<id>', methods=['GET', 'POST'])
def canada_organization_bulk_process(id: str, group_type: str = 'organization',
                                     is_organization: Optional[bool] = True,
                                     data: Optional[Dict[str, Any]] = None):
    """
    Redirects the Organization bulk action endpoint as it does not support
    the IPackageController and IResourceController implementations.
    """
    return h.redirect_to('%s.read' % group_type, id=id)


@canada_views.route('/create-pd-record/<owner_org>/<resource_name>',
                    methods=['GET', 'POST'])
def create_pd_record(owner_org: str, resource_name: str):
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

    choice_fields = _get_choice_fields(resource_name)
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
                    # type_ignore_reason: incomplete typing
                    err = dict({
                        k: list(format_trigger_error(v))
                        for (k, v) in
                        ve.error_dict['records'][0].items()  # type: ignore
                    }, **err)
                except AttributeError:
                    # type_ignore_reason: incomplete typing
                    if (
                      'duplicate key value violates unique constraint' in
                      ve.error_dict['records'][0]):  # type: ignore
                        err = dict({
                            k: [_("This record already exists")]
                            for k in pk_fields
                        }, **err)
                    elif (
                      'constraint_info' in ve.error_dict):
                        error_summary = _render_recombinant_constraint_errors(
                            lc, ve, chromo, 'upsert')
                    else:
                        log.warning('Failed to create %s record for org %s:\n%s',
                                    resource_name, owner_org, traceback.format_exc())
                        error_summary = _('Something went wrong, your record '
                                          'was not created. Please contact support.')
            # type_ignore_reason: incomplete typing
            elif ve.error_dict.get(
                    'info', {}).get('pgcode', '') == '23505':  # type: ignore
                err = dict({
                    k: [_("This record already exists")]
                    for k in pk_fields
                }, **err)
            else:
                log.warning('Failed to create %s record for org %s:\n%s',
                            resource_name, owner_org, traceback.format_exc())
                error_summary = _('Something went wrong, your record '
                                  'was not created. Please contact support.')

        if err or error_summary:
            return render('recombinant/create_pd_record.html',
                          extra_vars={
                              'data': data,
                              'resource_name': resource_name,
                              'chromo_title': chromo['title'],
                              'choice_fields': choice_fields,
                              'owner_org': rcomb['owner_org'],
                              # prevent rendering error on parent template
                              'pkg_dict': {},
                              'errors': err,
                              'error_summary': error_summary,
                          })

        h.flash_notice(_('Record Created'))

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


@canada_views.route('/update-pd-record/<owner_org>/<resource_name>/<pk>',
                    methods=['GET', 'POST'])
def update_pd_record(owner_org: str, resource_name: str, pk: str):
    pk_list = [_url_part_unescape(p) for p in pk.split(',')]

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

    choice_fields = _get_choice_fields(resource_name)
    pk_fields = aslist(chromo['datastore_primary_key'])
    pk_filter = dict(zip(pk_fields, pk_list))

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
                # method='update',    FIXME not raising ValidationErrors
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            try:
                # type_ignore_reason: incomplete typing
                err = dict({
                    k: list(format_trigger_error(v))
                    for (k, v) in ve.error_dict['records'][0].items()  # type: ignore
                }, **err)
            except AttributeError:
                log.warning('Failed to update %s record for org %s:\n%s',
                            resource_name, owner_org, traceback.format_exc())
                error_summary = _('Something went wrong, your record '
                                  'was not updated. Please contact support.')

        if err or error_summary:
            return render('recombinant/update_pd_record.html',
                          extra_vars={
                              'data': data,
                              'resource_name': resource_name,
                              'chromo_title': chromo['title'],
                              'choice_fields': choice_fields,
                              'pk_fields': pk_fields,
                              'owner_org': rcomb['owner_org'],
                              # prevent rendering error on parent template
                              'pkg_dict': {},
                              'errors': err,
                              'error_summary': error_summary})

        h.flash_notice(_('Record %s Updated') % ','.join(pk_list))

        return h.redirect_to(
            'recombinant.preview_table',
            resource_name=resource_name,
            owner_org=rcomb['owner_org'],
            )

    data = {}
    for f in chromo['fields']:
        if (
          not f.get('import_template_include', True) or
          f.get('published_resource_computed_field', False)):
            continue
        val = record[f['datastore_id']]
        if val and f.get('datastore_type') == 'money':
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
                      # prevent rendering error on parent template
                      'pkg_dict': {},
                      'errors': {},
                  })


@canada_views.route('/recombinant/<resource_name>', methods=['GET'])
def type_redirect(resource_name: str, dataset_id: Optional[str] = None):
    orgs = h.organizations_available('read')

    if not orgs:
        abort(404, _('No organizations found'))
    try:
        get_chromo(resource_name)
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
            dataset = get_action('package_show')(
                {'user': g.user}, {'id': dataset_id})
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


@canada_views.route('/recombinant/delete-selected-records/<resource_id>',
                    methods=['GET', 'POST'])
def delete_selected_records(resource_id: str):
    lc = LocalCKAN(username=g.user)

    if not h.check_access('datastore_records_delete',
                          {'resource_id': resource_id, 'filters': {}}):
        return abort(403, _('User {0} not authorized to update resource {1}'
                     .format(str(g.user), resource_id)))

    try:
        res = lc.action.resource_show(id=resource_id)
        pkg = lc.action.package_show(id=res['package_id'])
        org = lc.action.organization_show(id=pkg['owner_org'])
        dataset = lc.action.recombinant_show(
            dataset_type=pkg['type'], owner_org=org['name'])
    except (NotFound, NotAuthorized):
        return abort(404, _('Not found'))

    records = request.form.getlist('select-delete')

    if 'cancel' in request.form:
        return h.redirect_to('recombinant.preview_table',
                             resource_name=res['name'],
                             owner_org=org['name'],
                             )
    if request.method != 'POST' or 'confirm' not in request.form:
        return render('recombinant/confirm_select_delete.html',
                      extra_vars={
                          'dataset': dataset,
                          'resource': res,
                          'num': len(records),
                          'select_delete': ';'.join(records)})

    records = ''.join(records).split(';')

    pk_fields = recombinant_primary_key_fields(res['name'])
    pk = []
    for f in pk_fields:
        pk.append(f['datastore_id'])

    records_deleted = 0
    for r in records:
        filter = dict(zip(pk, r.split(',')))
        if filter:
            try:
                lc.action.datastore_records_delete(
                    resource_id=resource_id,
                    filters=filter
                )
                records_deleted += 1
            except NotFound:
                h.flash_error(_('Not found') + ' ' + str(filter))
            except ValidationError as e:
                if 'constraint_info' in e.error_dict:
                    error_message = _render_recombinant_constraint_errors(
                        lc, e, get_chromo(res['name']), 'delete')
                    h.flash_error(error_message)
                    return h.redirect_to('recombinant.preview_table',
                                         resource_name=res['name'],
                                         owner_org=org['name'])
                raise

    h.flash_success(_("{num} deleted.").format(num=records_deleted))

    return h.redirect_to(
        'recombinant.preview_table',
        resource_name=res['name'],
        owner_org=org['name'],
    )


def _clean_check_type_errors(post_data: Dict[str, Any],
                             fields: List[Dict[str, Any]],
                             pk_fields: List[str],
                             choice_fields: Dict[str, Any]) -> \
                                Tuple[Dict[str, Any], Dict[str, Any]]:
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
        if (
          not f.get('import_template_include', True) or
          f.get('published_resource_computed_field', False)):
            continue
        else:
            val = post_data.get(f['datastore_id'], '')
            if isinstance(val, list):
                val = ','.join(val)
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
                        err[f['datastore_id']] = [_('Number required')]
                elif f['datastore_type'] == 'int':
                    try:
                        int(val)
                    except ValueError:
                        err[f['datastore_id']] = [_('Integer required')]
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
    return render('home/quick_links.html',
                  extra_vars={'is_sysadmin': is_sysadmin(g.user)})


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
    data = clean_dict(unflatten(tuplize_dict(parse_params(request.form))))

    publish_date = data.get('publish_date', '')
    if not publish_date:
        h.flash_error(_('Invalid publish date'))
        return h.redirect_to('canada.ckanadmin_publish')
    publish_date = date_str_to_datetime(publish_date).strftime("%Y-%m-%d %H:%M:%S")

    # get a list of package id's from the for POST data
    publish_packages = data.get('publish', [])
    if isinstance(publish_packages, string_types):
        publish_packages = [publish_packages]
    count = len(publish_packages)
    for package_id in publish_packages:
        lc.action.package_patch(
            id=package_id,
            portal_release_date=publish_date,
        )

    # flash notice that records are published
    h.flash_notice(str(count) + _(' record(s) published.'))

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
    if (
      jobs and datetime.strptime(jobs[0]['created'], '%Y-%m-%dT%H:%M:%S') <
      (datetime.now() - timedelta(minutes=18))):
        warning = True

    return render('admin/jobs.html', extra_vars={'job_list': jobs,
                                                 'warning': warning})


@canada_views.route('/help', methods=['GET'])
def view_help():
    if not g.is_registry:
        return abort(404)
    return render('help.html', extra_vars={})


@canada_views.route('/datatable/<resource_name>/<resource_id>',
                    methods=['GET', 'POST'])
@csrf.exempt
def pd_datatable(resource_name: str, resource_id: str):
    params = parse_params(request.form)
    # type_ignore_reason: datatable param draw is int
    draw = int(params['draw'])  # type: ignore
    search_text = str(params['search[value]'])
    dt_query = str(params['dt_query'])
    if dt_query and not search_text:
        search_text = dt_query
    # type_ignore_reason: datatable param start is int
    offset = int(params['start'])  # type: ignore
    # type_ignore_reason: datatable param length is int
    limit = int(params['length'])  # type: ignore

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
    cols = []
    fids = []
    for f in chromo['fields']:
        if f.get('published_resource_computed_field', False):
            continue
        cols.append(f['datastore_id'])
        fids.append(f['datastore_id'])
    # Select | (Edit) | ...
    prefix_cols = 2 if chromo.get('edit_form', False) and can_edit else 1

    sort_list = []
    i = 0
    while True:
        if 'order[%d][column]' % i not in params:
            break
        # type_ignore_reason: datatable param 'order[%d][column] is int
        sort_by_num = int(params['order[%d][column]' % i])  # type: ignore
        sort_order = (
            'desc' if params['order[%d][dir]' % i] == 'desc'
            else 'asc')
        sort_list.append(
            cols[sort_by_num - prefix_cols] + ' ' + sort_order + ' nulls last')
        i += 1

    response = lc.action.datastore_search(
        q=search_text,
        resource_id=resource_id,
        offset=offset,
        limit=limit,
        sort=', '.join(sort_list),
    )

    aadata = [
        ['<i aria-hidden="true" class="fas fa-expand-alt"></i>'] +  # Expand column
        ['<input type="checkbox">'] +  # Select column
        [datatablify(row.get(colname, ''), colname, chromo) for colname in cols]
        for row in response['records']]

    if chromo.get('edit_form', False) and can_edit:
        res = lc.action.resource_show(id=resource_id)
        pkg = lc.action.package_show(id=res['package_id'])
        pkids = [fids.index(k) for k in aslist(chromo['datastore_primary_key'])]
        for row in aadata:
            row.insert(2, (
                    '<a href="{0}" aria-label="' + _("Edit") + '">'
                    '<i class="fa fa-lg fa-edit" aria-hidden="true"></i></a>').format(
                    h.url_for(
                        'canada.update_pd_record',
                        owner_org=pkg['organization']['name'],
                        resource_name=resource_name,
                        pk=','.join(_url_part_escape(row[i+1]) for i in pkids)
                    )
                )
            )

    return json.dumps({
        'draw': draw,
        'iTotalRecords': unfiltered_response.get('total', 0),
        'iTotalDisplayRecords': response.get('total', 0),
        'aaData': aadata,
    })


def datatablify(v: Any, colname: str, chromo: Dict[str, Any]) -> str:
    '''
    format value from datastore v for display in a datatable preview
    '''
    chromo_field = None
    for f in chromo['fields']:
        if f['datastore_id'] == colname:
            chromo_field = f
            break
    if v is None:
        return ''
    if v is True:
        return 'TRUE'
    if v is False:
        return 'FALSE'
    if isinstance(v, list):
        return ', '.join(str(e) for e in v)
    if colname in ('record_created', 'record_modified') and v:
        return canada_date_str_to_datetime(v).replace(tzinfo=utc).astimezone(
            ottawa_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    if chromo_field and chromo_field.get('datastore_type') == 'money':
        if isinstance(v, str) and '$' in v:
            return v
        return '${:,.2f}'.format(v)
    return str(v)


@canada_views.route('/fgpv-vpgf/<pkg_id>', methods=['GET'])
def fgpv_vpgf(pkg_id: str):
    return render('fgpv_vpgf/index.html', extra_vars={
        'pkg_id': pkg_id,
    })


@canada_views.route('/organization/autocomplete', methods=['GET'])
def organization_autocomplete():
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20)
    organization_list = []

    if q:
        context = cast(Context, {'user': g.user, 'model': model, 'ignore_auth': True})
        data_dict = {'q': q, 'limit': limit}
        organization_list = get_action(
            'organization_autocomplete'
        )(context, data_dict)

    def _org_key(org: Dict[str, Any]) -> str:
        return org['title'].split(' | ')[-1 if lang() == 'fr' else 0]

    return_list = [{
        'id': o['id'],
        'name': o['name'],
        'title': _org_key(o)
    } for o in organization_list]

    return _finish_ok(return_list)


@canada_views.route('/api/<int(min=1, max=2):ver>/action/<logic_function>',
                    methods=['GET', 'POST'])
@canada_views.route('/api/action/<logic_function>', methods=['GET', 'POST'])
@canada_views.route('/api/<int(min=3, max={0}):ver>/action/<logic_function>'.format(
                    API_MAX_VERSION), methods=['GET', 'POST'])
def action(logic_function: str,
           ver: int = API_DEFAULT_VERSION):
    '''Main endpoint for the action API (v3)

    Creates a dict with the incoming request data and calls the appropiate
    logic function. Returns a JSON response with the following keys:

        * ``help``: A URL to the docstring for the specified action
        * ``success``: A boolean indicating if the request was successful or
                an exception was raised
        * ``result``: The output of the action, generally an Object or an Array

    Canada Fork:
        We keep version 1 and 2 endpoints just incase any systems
        are still using that. We also have -1 to version to return the
        context and request_data for extra logging. And if the request is a
        POST request, we want to not authorize any PD type.
    '''
    try:
        function = get_action(logic_function)
    except Exception:
        return api_view_action(logic_function, ver)

    try:
        side_effect_free = getattr(function, 'side_effect_free', False)
        request_data = _get_request_data(try_url_params=side_effect_free)
    except Exception:
        return api_view_action(logic_function, ver)

    if not request_data:
        return api_view_action(logic_function, ver)

    context = cast(Context, {'model': model, 'session': model.Session,
                             'user': g.user, 'api_version': ver,
                             'auth_user_obj': g.userobj})

    return_dict = {'help': h.url_for('api.action',
                                     logic_function='help_show',
                                     ver=ver,
                                     name=logic_function,
                                     _external=True)}

    # extra logging here
    id = request_data.get('id', request_data.get(
        'package_id', request_data.get('resource_id')))
    pkg_dict = _get_package_from_api_request(logic_function, id, context)
    if pkg_dict:
        _log_api_access(request_data, pkg_dict)

    # prevent PD types from being POSTed to via the API, but allow DataStore POSTing
    if request.method == 'POST' and not logic_function.startswith('datastore'):
        package_type = pkg_dict.get('type') if pkg_dict \
            else request_data.get('package_type', request_data.get('type'))
        if package_type and package_type in h.recombinant_get_types():
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False

            return _finish(403, return_dict, content_type='json')

    return api_view_action(logic_function, ver)


def _get_package_from_api_request(logic_function: str,
                                  id: str,
                                  context: Context) -> Optional[Dict[str, Any]]:
    """
    Tries to return the package for an API request
    """
    if not id:
        return None
    if (
      logic_function.startswith('group') or
      logic_function.startswith('organization') or
      logic_function.startswith('urser')):
        return None
    if (
      logic_function.startswith('resource') or
      logic_function.startswith('datastore')):
        try:
            res_dict = get_action('resource_show')(context, {'id': id})
            id = res_dict['package_id']
        except (NotAuthorized, NotFound):
            pass
    try:
        pkg_dict = get_action('package_show')(context, {'id': id})
        return pkg_dict
    except (NotAuthorized, NotFound):
        return None


def _log_api_access(request_data: Dict[str, Any], pkg_dict: Dict[str, Any]):
    org = model.Group.get(pkg_dict.get('owner_org'))
    if not org:
        org_name = 'Unknown'
    else:
        org_name = org.name
    g.log_extra = 'org={o} type={t} id={i}'.format(
        o=org_name,
        t=pkg_dict.get('type'),
        i=pkg_dict.get('id'))
    if 'resource_id' in request_data:
        g.log_extra += ' rid={0}'.format(request_data['resource_id'])


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


def notify_ckan_user_create(email: str,
                            fullname: str,
                            username: str,
                            phoneno: str,
                            dept: str):
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
                    'New Registry Account Created / Nouveau compte'
                    ' cr\u00e9\u00e9 dans le registre de Gouvernement ouvert'
                ),
                render(
                    'user/new_user_email.html',
                    extra_vars=xtra_vars
                )
            )
    except ckan.lib.mailer.MailerException as m:
        log = getLogger('ckanext')
        log.error(getattr(m, 'message', None))

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
                'Welcome to the Open Government Registry / '
                'Bienvenue au Registre de Gouvernement Ouvert'
            ),
            render(
                'user/user_welcome_email.html',
                extra_vars=xtra_vars
            )
        )
    except (ckan.lib.mailer.MailerException, socket_error) as m:
        log = getLogger('ckanext')
        log.error(getattr(m, 'message', None))


@canada_views.route('/organization/member_dump/<id>', methods=['GET'])
def organization_member_dump(id: str):
    records_format = 'csv'

    org_dict = model.Group.get(id)
    if not org_dict:
        abort(404, _('Organization not found'))

    context = cast(Context, {'model': model,
                             'session': model.Session,
                             'user': g.user})

    try:
        check_access('organization_member_create', context, {'id': id})
    except NotAuthorized:
        abort(404, _('Not authorized to access {org_name} members download'.format(
            org_name=org_dict.title)))

    try:
        members = get_action('member_list')(context, {
            'id': id,
            'object_type': 'user',
            'records_format': records_format,
            'include_total': False,
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

    file_name = '{org_id}-{members}'.format(
            org_id=org_dict.name,
            members=_('members'))

    output_stream.seek(0)
    response = make_response(output_stream.read())
    output_stream.close()
    content_disposition = 'attachment; filename="{name}.csv"'.format(
                                    name=file_name)
    content_type = b'text/csv; charset=utf-8'
    # type_ignore_reason: bytes allowed and expected in CKAN
    response.headers['Content-Type'] = content_type  # type: ignore
    response.headers['Content-Disposition'] = content_disposition

    return response


@canada_views.route('/organization/members/<id>', methods=['GET', 'POST'])
def members(id: str):
    """
    Copied from core. Permissions for Editors to view members in GET.
    """
    extra_vars = {}
    set_org(True)
    context = cast(Context, {'model': model, 'session': model.Session, 'user': g.user})

    try:
        data_dict: Dict[str, Any] = {'id': id}
        if request.method == 'POST':
            auth_action = 'group_edit_permissions'
        else:
            auth_action = 'view_org_members'
        check_access(auth_action, context, data_dict)
        members = get_action('member_list')(context, {
            'id': id,
            'object_type': 'user'
        })
        data_dict['include_datasets'] = False
        group_dict = get_action('organization_show')(context, data_dict)
    except NotFound:
        abort(404, _('Organization not found'))
    except NotAuthorized:
        if request.method == 'POST':
            error_message = _('User %r not authorized to edit members of %s') % \
                (g.user, id)
        else:
            error_message = _('User %r not authorized to view members of %s') % \
                (g.user, id)
        abort(403, error_message)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.members = members
    g.group_dict = group_dict

    extra_vars = {
        "members": members,
        "group_dict": group_dict,
        "group_type": 'organization'
    }
    return render('organization/members.html', extra_vars)


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
    return render('admin/index.html', extra_vars={'sysadmins': sysadmins})


@canada_views.route('/ckan-admin/config', methods=['GET', 'POST'])
def ckan_admin_config():
    """
    404 this page always.
    """
    return abort(404)


@canada_views.route('/ckan-admin/portal-sync', methods=['GET'])
def ckan_admin_portal_sync():
    """
    Lists any packages that are out of date with the Portal.
    """
    try:
        check_access('list_out_of_sync_packages', {'user': g.user})
    except NotAuthorized:
        return abort(403)

    page_number = h.get_page_number(request.args) or 1
    limit = 25
    start = limit * (page_number - 1)
    extra_vars = {}

    out_of_sync_packages = get_action('list_out_of_sync_packages')(
        {'user': g.user}, {'limit': limit, 'start': start})
    extra_vars['out_of_sync_packages'] = out_of_sync_packages

    def _basic_pager_uri(page: Union[int, str], text: str):
        return h.url_for('canada.ckan_admin_portal_sync', page=page)
    pager_url = partial(_basic_pager_uri, page=page_number, text='')

    extra_vars['page'] = Page(
        collection=out_of_sync_packages['results'],
        page=page_number,
        url=pager_url,
        item_count=out_of_sync_packages.get('count', 0),
        items_per_page=limit
    )
    extra_vars['page'].items = out_of_sync_packages['results']

    # TODO: remove in CKAN 2.11??
    setattr(g, 'page', extra_vars['page'])

    return render('admin/portal_sync.html', extra_vars=extra_vars)
