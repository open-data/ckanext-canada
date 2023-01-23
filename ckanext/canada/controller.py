# -*- coding: utf-8 -*-
import json
import socket
from logging import getLogger

from webob.exc import HTTPFound
from pytz import timezone, utc

import pkg_resources
import lxml.etree as ET
import lxml.html as html
from ckan.lib.base import model
from ckan.logic import schema
from ckan.controllers.user import UserController
from ckan.controllers.api import ApiController, DataError, NotFound, search
from ckan.lib.helpers import (
    Page,
    date_str_to_datetime,
    render_markdown,
)
from ckan.lib import i18n
import ckan.lib.jsonp as jsonp
from ckan.controllers.package import PackageController

from ckanext.canada.helpers import normalize_strip_accents, canada_date_str_to_datetime
from ckanext.canada.urlsafe import url_part_escape, url_part_unescape
from ckan.plugins.toolkit import _, config

from ckantoolkit import (
    c,
    BaseController,
    h,
    render,
    request,
    abort,
    get_action,
    check_access,
    get_validator,
    aslist,
    )


from ckanapi import LocalCKAN, NotAuthorized, ValidationError

int_validator = get_validator('int_validator')

ottawa_tz = timezone('America/Montreal')

log = getLogger(__name__)


class CanadaController(BaseController):
    def home(self):
        if not c.user:
            h.redirect_to(controller='user', action='login')

        is_new = not h.check_access('package_create')

        if is_new:
            return h.redirect_to(controller='package', action='search')
        return h.redirect_to(
            controller='ckanext.canada.controller:CanadaController',
            action='links')

    def links(self):
        return render('home/quick_links.html')

    def view_guidelines(self):
        return render('guidelines.html')

    def view_help(self):
        def _get_help_text(language):
            return pkg_resources.resource_string(
                __name__,
                '/'.join(['public', 'static', 'faq_{language}.md'.format(
                    language=language
                )])
            )

        try:
            # Try to load FAQ text for the user's language.
            faq_text = _get_help_text(c.language)
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

    def organization_index(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if c.userobj:
            context['user_id'] = c.userobj.id
            context['user_is_admin'] = c.userobj.sysadmin

        results = get_action('organization_list')(context, data_dict)
        c.group_type = data_dict['type']

        def org_key(org):
            title = org['title'].split(' | ')[-1 if c.language == 'fr' else 0]
            return normalize_strip_accents(title)

        results.sort(key=org_key)

        c.page = Page(
            collection=results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=1000
        )
        return render('organization/index.html')

    def datatable(self, resource_name, resource_id):
        draw = int(request.params['draw'])
        search_text = unicode(request.params['search[value]'])
        offset = int(request.params['start'])
        limit = int(request.params['length'])

        chromo = h.recombinant_get_chromo(resource_name)
        lc = LocalCKAN(username=c.user)
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

        cols = [f['datastore_id'] for f in chromo['fields']]
        prefix_cols = 2 if chromo.get('edit_form', False) else 1  # Select | (Edit) | ...

        sort_list = []
        i = 0
        while True:
            if u'order[%d][column]' % i not in request.params:
                break
            sort_by_num = int(request.params[u'order[%d][column]' % i])
            sort_order = (
                u'desc' if request.params[u'order[%d][dir]' % i] == u'desc'
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

        if chromo.get('edit_form', False):
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

    def package_delete(self, pkg_id):
        h.flash_success(_(
            '<strong>Note</strong><br> The dataset has been removed from'
            ' the Open Government Portal. <br/> The record may re-appear'
            ' if it is re-harvested or updated. Please ensure that the'
            ' record is deleted and purged from the source catalogue in'
            ' order to prevent it from reappearing.'
            ),
            allow_html=True
        )
        lc = LocalCKAN(username=c.user)
        lc.action.package_delete(id=pkg_id)

        return h.redirect_to(
            controller='package',
            action='search'
        )

    def package_undelete(self, pkg_id):
        h.flash_success(_(
            '<strong>Note</strong><br> The record has been restored.'),
            allow_html=True
        )

        lc = LocalCKAN(username=c.user)
        lc.action.package_patch(
            id=pkg_id,
            state='active'
        )

        return h.redirect_to(
            controller='package',
            action='read',
            id=pkg_id
        )

    @jsonp.jsonpify
    def organization_autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        organization_list = []

        if q:
            context = {'user': c.user, 'model': model}
            data_dict = {'q': q, 'limit': limit}
            organization_list = get_action(
                'organization_autocomplete'
            )(context, data_dict)

        def _org_key(org):
            return org['title'].split(' | ')[-1 if c.language == 'fr' else 0]

        return [{
            'id': o['id'],
            'name': _org_key(o),
            'title': _org_key(o)
        } for o in organization_list]

    def fgpv_vpgf(self, pkg_id):
        return render('fgpv_vpgf/index.html', extra_vars={
            'pkg_id': pkg_id,
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


class CanadaUserController(UserController):
    def register(self, data=None, errors=None, error_summary=None):
        '''GET to display a form for registering a new user.
           or POST the form data to actually do the user registration.
           The bulk of this code is pulled directly from
           ckan/controlllers/user.py
        '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': schema.user_new_form_schema(),
                   'save': 'save' in request.params}

        try:
            check_access('user_create', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a user'))

        if context['save'] and not data:
            try:
                return self._save_new(context)
            except HTTPFound:
                # redirected after successful user create
                import ckan.lib.mailer
                # checks if there is a custom function "notify_ckan_user_create" in the mailer (added by ckanext-gcnotify)
                getattr(
                  ckan.lib.mailer,
                  "notify_ckan_user_create",
                  notify_ckan_user_create
                )(
                  email=request.params.get('email', ''),
                  fullname=request.params.get('fullname', ''),
                  username=request.params.get('name', ''),
                  phoneno=request.params.get('phoneno', ''),
                  dept=request.params.get('department', ''))
                notice_no_access()
                raise

        if c.user and not data and not is_sysadmin(c.user):
            # #1799 Don't offer the registration form if already logged in
            return render('user/logout_first.html')

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        d = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.is_sysadmin = is_sysadmin(c.user)
        c.form = render('user/new_user_form.html', extra_vars=d)
        return render('user/new.html')

    def reports(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'for_view': True}
        data_dict = {'id': id,
                     'user_obj': c.userobj,
                     'include_datasets': True,
                     'include_num_followers': True}

        context['with_related'] = True

        self._setup_template_variables(context, data_dict)

        if c.is_myself:
            return render('user/reports.html')
        abort(403)


class CanadaAdminController(PackageController):

    def _search_template(self, package_type):
        return 'admin/publish_search.html'

    def _guess_package_type(self, expecting_name=False):
        # this is a bit unortodox, but this method allows us to conveniently
        # alter the search method without much code duplication.
        if not is_sysadmin(c.user):
            abort(401, _('Not authorized to see this page'))

        # always set ready_to_publish to true for the publishing interface
        request.GET['ready_to_publish'] = u'true'
        request.GET['imso_approval'] = u'true'

        # This MUST be None, otherwise the default filtering will apply and
        # restrict to just dataset_type=dataset.
        return None

    def publish(self):
        lc = LocalCKAN(username=c.user)

        publish_date = date_str_to_datetime(
            request.str_POST['publish_date']
        ).strftime("%Y-%m-%d %H:%M:%S")

        # get a list of package id's from the for POST data
        count = 0
        for key, package_id in request.str_POST.iteritems():
            if key == 'publish':
                lc.action.package_patch(
                    id=package_id,
                    portal_release_date=publish_date,
                )
                count += 1

        # flash notice that records are published
        h.flash_notice(str(count) + _(u' record(s) published.'))

        # return us to the publishing interface
        return h.redirect_to(h.url_for('ckanadmin_publish'))


class CanadaApiController(ApiController):
    def action(self, logic_function, ver=None):
        log = getLogger('ckanext')
        # Copied from ApiController so we can log details of some API calls
        # XXX: for later ckans look for a better hook
        try:
            function = get_action(logic_function)
        except KeyError:
            log.info('Can\'t find logic function: %s', logic_function)
            return self._finish_bad_request(
                _('Action name not known: %s') % logic_function)

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}
        model.Session()._context = context

        return_dict = {'help': h.url_for(controller='api',
                                         action='action',
                                         logic_function='help_show',
                                         ver=ver,
                                         name=logic_function,
                                         qualified=True,
                                         )
                       }
        try:
            side_effect_free = getattr(function, 'side_effect_free', False)
            request_data = self._get_request_data(try_url_params=
                                                  side_effect_free)
        except ValueError, inst:
            log.info('Bad Action API request data: %s', inst)
            return self._finish_bad_request(
                _('JSON Error: %s') % inst)
        if not isinstance(request_data, dict):
            # this occurs if request_data is blank
            log.info('Bad Action API request data - not dict: %r',
                     request_data)
            return self._finish_bad_request(
                _('Bad request data: %s') %
                'Request data JSON decoded to %r but '
                'it needs to be a dictionary.' % request_data)
        # if callback is specified we do not want to send that to the search
        if 'callback' in request_data:
            del request_data['callback']
            c.user = None
            c.userobj = None
            context['user'] = None
            context['auth_user_obj'] = None
        try:
            result = function(context, request_data)
            # XXX extra logging here
            _log_api_access(context, request_data)
            return_dict['success'] = True
            return_dict['result'] = result
        except DataError, e:
            log.info('Format incorrect (Action API): %s - %s',
                     e.error, request_data)
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except NotAuthorized, e:
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False

            if unicode(e):
                return_dict['error']['message'] += u': %s' % e

            return self._finish(403, return_dict, content_type='json')
        except NotFound, e:
            return_dict['error'] = {'__type': 'Not Found Error',
                                    'message': _('Not found')}
            if unicode(e):
                return_dict['error']['message'] += u': %s' % e
            return_dict['success'] = False
            return self._finish(404, return_dict, content_type='json')
        except ValidationError, e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            return_dict['success'] = False
            # CS nasty_string ignore
            log.info('Validation error (Action API): %r', str(e.error_dict))
            return self._finish(409, return_dict, content_type='json')
        except search.SearchQueryError, e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except search.SearchError, e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return_dict['success'] = False
            return self._finish(409, return_dict, content_type='json')
        except search.SearchIndexError, e:
            return_dict['error'] = {
                '__type': 'Search Index Error',
                'message': 'Unable to add package to search index: %s' %
                           str(e)}
            return_dict['success'] = False
            return self._finish(500, return_dict, content_type='json')
        return self._finish_ok(return_dict)


def _log_api_access(context, data_dict):
    if 'package' not in context:
        if 'resource_id' not in data_dict:
            return
        res = model.Resource.get(data_dict['resource_id'])
        if not res:
            return
        pkg = res.package
    else:
        pkg = context['package']
    org = model.Group.get(pkg.owner_org)
    c.log_extra = u'org={o} type={t} id={i}'.format(
        o=org.name,
        t=pkg.type,
        i=pkg.id)
    if 'resource_id' in data_dict:
        c.log_extra += u' rid={0}'.format(data_dict['resource_id'])


def notice_no_access():
    '''flash_notice if logged-in user can't actually do anything yet'''
    if h.check_access('package_create'):
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
    except (ckan.lib.mailer.MailerException, socket.error) as m:
        log = getLogger('ckanext')
        log.error(m.message)


class CanadaDatastoreController(BaseController):
    def delete_datastore_table(self, id, resource_id):
        if request.method == 'POST':
            lc = LocalCKAN(username=c.user)

            try:
                lc.action.datastore_delete(
                    resource_id=resource_id,
                    force=True,  # FIXME: check url_type first?
                )
            except NotAuthorized:
                return abort(403, _('Unauthorized'))
        # FIXME else: render confirmation page for non-JS users
        return h.redirect_to(
            controller='ckanext.xloader.controllers:ResourceDataController',
            action='resource_data',
            id=id,
            resource_id=resource_id
        )

