import json
import decimal
import pkg_resources
import lxml.etree as ET
import lxml.html as html
from pytz import timezone, utc
from socket import error as socket_error
from logging import getLogger
import unicodecsv
from codecs import BOM_UTF8
from six import string_types, PY2
from datetime import datetime, timedelta

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
from ckan.lib.base import model
import ckan.lib.jsonp as jsonp
from ckan.lib.helpers import (
    date_str_to_datetime,
    render_markdown,
    lang
)

from ckan.views.dataset import (
    EditView as DatasetEditView,
    search as dataset_search,
    CreateView as DatasetCreateView,
    activity as dataset_activity
)
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

if PY2:
    from cStringIO import StringIO
else:
    from io import StringIO

MAX_JOB_QUEUE_LIST_SIZE = 25

canada_views = Blueprint('canada', __name__)
ottawa_tz = timezone('America/Montreal')


class IntentionalServerError(Exception):
    pass


@canada_views.route('/user/login', methods=['GET'])
def login():
    from ckan.views.user import _get_repoze_handler

    came_from = h.url_for(u'canada.logged_in')
    g.login_handler = h.url_for(
        _get_repoze_handler(u'login_handler_path'), came_from=came_from)
    return render(u'user/login.html', {})


@canada_views.route('/logged_in', methods=['GET'])
def logged_in():
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
    if uri[0]:
        if uri[0] == 'activity':  # allow activity route
            return dataset_activity(package_type, uri[1])
        id = uri[0]
        package_type = _get_package_type_from_dict(id, package_type)
    if package_type in h.recombinant_get_types():
        return type_redirect(package_type)
    return abort(404)


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


def canada_search(package_type):
    if h.is_registry() and not g.user:
        return abort(403)
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
        f['datastore_id']: [
            {'value': k,
             'label': k + separator + v if _form_choices_prefix_code(f['datastore_id'], chromo) else v
             } for (k, v) in f['choices']]
        for f in h.recombinant_choice_fields(resource_name)}


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
                    err = dict({
                        k: [_("This record already exists")]
                        for k in pk_fields
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
    if is_sysadmin(g.user):
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


@canada_views.route('/', methods=['GET'])
def home():
    if not h.is_registry():
        return h.redirect_to('dataset.search')
    if not g.user:
        return h.redirect_to('user.login')

    is_new = not h.check_access('package_create')

    if is_new:
        return h.redirect_to('dataset.search')
    return h.redirect_to('canada.links')


@canada_views.route('/links', methods=['GET'])
def links():
    if not h.is_registry():
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


@canada_views.route('/dataset/<id>/delete-datastore-table/<resource_id>', methods=['GET', 'POST'])
def delete_datastore_table(id, resource_id):
    if u'cancel' in request.form:
        return h.redirect_to(u'xloader.resource_data', id=id, resource_id=resource_id)

    if request.method == 'POST':
        lc = LocalCKAN(username=g.user)

        try:
            lc.action.datastore_delete(
                resource_id=resource_id,
                force=True,  # FIXME: check url_type first?
            )
        except NotAuthorized:
            return abort(403, _(u'Unauthorized to delete resource %s') % resource_id)

        h.flash_notice(_(u'DataStore table and Data Dictionary deleted for resource %s') % resource_id)

        return h.redirect_to(
            'xloader.resource_data',
            id=id,
            resource_id=resource_id
        )
    else:
        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.resource_id = resource_id
        g.package_id = id

        extra_vars = {
            u"resource_id": resource_id,
            u"package_id": id
        }
        return render(u'canada/confirm_datastore_delete.html', extra_vars)


@canada_views.route('/help', methods=['GET'])
def view_help():
    def _get_help_text(language):
        return pkg_resources.resource_string(
            __name__,
            '/'.join(['public', 'static', 'faq_{language}.md'.format(
                language=language
            )])
        )

    try:
        # Try to load FAQ text for the user's language.
        faq_text = _get_help_text(lang())
    except IOError:
        # Fall back to using English if no local language could be found.
        faq_text = _get_help_text(u'en')

    # Convert the markdown to HTML ...
    faq_html = render_markdown(faq_text.decode("utf-8"), allow_html=True)
    h = html.fromstring(faq_html)

    # Get every FAQ point header.
    for faq_section in h.xpath('.//h2'):

        details = ET.Element('details')
        summary = ET.Element('summary')

        # Place the new details tag where the FAQ section header used to
        # be.
        faq_section.addprevious(details)

        # Get all the text that follows the FAQ header.
        while True:
            next_node = faq_section.getnext()
            if next_node is None or next_node.tag in ('h1', 'h2'):
                break
            # ... and add it to the details.
            details.append(next_node)

        # Move the FAQ header to the top of the summary tag.
        summary.insert(0, faq_section)
        # Move the summary tag to the top of the details tag.
        details.insert(0, summary)

        # We don't actually want the FAQ headers to be headings, so strip
        # the tags and just leave the text.
        faq_section.drop_tag()

    # Get FAQ group header and set it as heading 2 to comply with
    # accessible heading ranks
    for faq_group in h.xpath('//h1'):
        faq_group.tag = 'h2'

    return render('help.html', extra_vars={
        'faq_html': html.tostring(h),
        # For use with the inline debugger.
        'faq_text': faq_text
    })


@canada_views.route('/datatable/<resource_name>/<resource_id>', methods=['GET', 'POST'])
def datatable(resource_name, resource_id):
    params = parse_params(request.form)
    draw = int(params['draw'])
    search_text = unicode(params['search[value]'])
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
        [datatablify(row.get(colname, u''), colname) for colname in cols]
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


def datatablify(v, colname):
    '''
    format value from datastore v for display in a datatable preview
    '''
    if v is None:
        return u''
    if v is True:
        return u'TRUE'
    if v is False:
        return u'FALSE'
    if isinstance(v, list):
        return u', '.join(unicode(e) for e in v)
    if colname in ('record_created', 'record_modified') and v:
        return canada_date_str_to_datetime(v).replace(tzinfo=utc).astimezone(
            ottawa_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    return unicode(v)


@canada_views.route('/fgpv-vpgf/<pkg_id>', methods=['GET'])
def fgpv_vpgf(pkg_id):
    return render('fgpv_vpgf/index.html', extra_vars={
        'pkg_id': pkg_id,
    })


@jsonp.jsonpify
@canada_views.route('/organization/autocomplete', methods=['GET'])
def organization_autocomplete():
    q = request.args.get('q', '')
    limit = request.args.get('limit', 20)
    organization_list = []

    if q:
        context = {'user': g.user, 'model': model}
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
    output_stream.write(BOM_UTF8)
    unicodecsv.writer(output_stream, encoding=u'utf-8').writerows(results)

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
