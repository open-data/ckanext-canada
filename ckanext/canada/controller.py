# -*- coding: utf-8 -*-
import json
import socket
from logging import getLogger
import decimal

import webhelpers.feedgenerator
from webob.exc import HTTPFound
from pytz import timezone, utc

import pkg_resources
import lxml.etree as ET
import lxml.html as html
from ckan.lib.base import model
from ckan.logic import schema
from ckan.controllers.user import UserController
from ckan.controllers.api import ApiController, DataError, NotFound, search
from ckan.authz import is_sysadmin
from ckan.lib.helpers import (
    Page,
    date_str_to_datetime,
    url,
    render_markdown,
)
from ckan.controllers.feed import (
    FeedController,
    _package_search,
    _create_atom_id,
    _FixedAtom1Feed
)
from ckan.lib import i18n
import ckan.lib.jsonp as jsonp
from ckan.controllers.package import PackageController
from ckan.logic import parse_params

from ckanext.canada.helpers import normalize_strip_accents, canada_date_str_to_datetime
from ckanext.canada.urlsafe import url_part_escape, url_part_unescape
from pylons.i18n import _
from pylons import config, session

from ckantoolkit import (
    c,
    BaseController,
    h,
    render,
    request,
    response,
    abort,
    get_action,
    check_access,
    get_validator,
    Invalid,
    aslist,
    )


from ckanapi import LocalCKAN, NotAuthorized, ValidationError
from ckanext.recombinant.datatypes import canonicalize
from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.errors import RecombinantException

int_validator = get_validator('int_validator')

ottawa_tz = timezone('America/Montreal')

log = getLogger(__name__)

class IntentionalServerError(Exception):
    pass


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

    def server_error(self):
        raise IntentionalServerError()

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
                            controller='ckanext.canada.controller:PDUpdateController',
                            action='update_pd_record',
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


class CanadaDatasetController(PackageController):
    def edit(self, id, data=None, errors=None, error_summary=None):
        try:
            return super(CanadaDatasetController, self).edit(
                id, data, errors, error_summary)
        except HTTPFound:
            if c.pkg_dict['type'] == 'prop':
                h.flash_success(_(u'The status has been added / updated for this suggested  dataset. This update will be reflected on open.canada.ca shortly.'))
            raise

    def resource_edit(self, id, resource_id, data=None, errors=None,
                      error_summary=None):
        try:
            return super(CanadaDatasetController, self).resource_edit(
                id, resource_id, data, errors, error_summary)
        except HTTPFound:
            h.flash_success(_(u'Resource updated.'))
            # resource read page is unfinished, return to dataset page
            h.redirect_to(controller='package', action='read', id=id)


class CanadaUserController(UserController):
    def logged_in(self):
        # we need to set the language via a redirect

        # Lang is not being retrieved properly by the Babel i18n lib in
        # this redirect, so using this clunky workaround for now.
        lang = session.pop('lang', None)
        if lang is None:
            came_from = request.params.get('came_from', '')
            if came_from.startswith('/fr'):
                lang = 'fr'
            else:
                lang = 'en'

        session.save()

        # we need to set the language explicitly here or the flash
        # messages will not be translated.
        i18n.set_lang(lang)

        if c.user:
            context = None
            data_dict = {'id': c.user}

            user_dict = get_action('user_show')(context, data_dict)

            h.flash_success(
                _('<strong>Note</strong><br>{0} is now logged in').format(
                    user_dict['display_name']
                ),
                allow_html=True
            )

            notice_no_access()

            return h.redirect_to(
                controller='ckanext.canada.controller:CanadaController',
                action='home',
                locale=lang)
        else:
            error_summary = _('Login failed. Bad username or password.')
            # replace redirect with a direct call to login controller
            # pass error_summary to controller as error
            # so that it can be captured for GA events in our overridden templates
            return UserController.login(self, error_summary)

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
                notify_ckan_user_create(
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


class CanadaFeedController(FeedController):
    def general(self):
        data_dict, params = self._parse_url_params()
        data_dict['q'] = '*:*'

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action='general')

        feed_url = self._feed_url(params,
                                  controller='feed',
                                  action='general')

        alternate_url = self._alternate_url(params)

        return self.output_feed(
            results,
            feed_title=_(u'Open Government Dataset Feed'),
            feed_description='',
            feed_link=alternate_url,
            feed_guid=_create_atom_id(
                u'/feeds/dataset.atom'),
            feed_url=feed_url,
            navigation_urls=navigation_urls
        )

    def output_feed(self, results, feed_title, feed_description,
                    feed_link, feed_url, navigation_urls, feed_guid):

        author_name = config.get('ckan.feeds.author_name', '').strip() or \
            config.get('ckan.site_id', '').strip()
        author_link = config.get('ckan.feeds.author_link', '').strip() or \
            config.get('ckan.site_url', '').strip()

        feed = _FixedAtom1Feed(
            title=feed_title,
            link=feed_link,
            description=feed_description,
            language=u'en',
            author_name=author_name,
            author_link=author_link,
            feed_guid=feed_guid,
            feed_url=feed_url,
            previous_page=navigation_urls['previous'],
            next_page=navigation_urls['next'],
            first_page=navigation_urls['first'],
            last_page=navigation_urls['last'],
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
                    self.base_url + url(str(
                        '/api/action/package_show?id=%s' % pkg['name'])),
                    unicode(len(json.dumps(pkg))),   # TODO fix this
                    u'application/json')
            )
        response.content_type = feed.mime_type
        return feed.writeString('utf-8')


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


class PDUpdateController(BaseController):

    def create_pd_record(self, owner_org, resource_name):
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

        choice_fields = {}
        for f in h.recombinant_choice_fields(resource_name):
            for r in chromo['fields']:
                if r['datastore_id'] == f['datastore_id'] and \
                        r.get('form_full_text_choices', False):
                    choice_fields[f['datastore_id']] = [{'value': k,
                                                         'label': k + ': ' + v}
                                                        for (k, v) in f['choices']]
            if f['datastore_id'] not in choice_fields:
                choice_fields[f['datastore_id']] = [{'value': k, 'label': v}
                                                    for (k, v) in f['choices']]

        pk_fields = aslist(chromo['datastore_primary_key'])

        if request.method == 'POST':
            post_data = parse_params(request.POST, ignore_keys=['save'])

            if 'cancel' in post_data:
                return h.redirect_to(h.url_for(
                    controller='ckanext.recombinant.controller:UploadController',
                    action='preview_table',
                    resource_name=resource_name,
                    owner_org=rcomb['owner_org'],
                    ))

            data, err = clean_check_type_errors(
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
                                  'errors': err,
                              })

            h.flash_notice(_(u'Record Created'))

            return h.redirect_to(h.url_for(
                controller='ckanext.recombinant.controller:UploadController',
                action='preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
            ))

        return render('recombinant/create_pd_record.html',
                      extra_vars={
                          'data': {},
                          'resource_name': resource_name,
                          'chromo_title': chromo['title'],
                          'choice_fields': choice_fields,
                          'owner_org': rcomb['owner_org'],
                          'errors': {},
                      })

    def update_pd_record(self, owner_org, resource_name, pk):
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

        choice_fields = {}
        for f in h.recombinant_choice_fields(resource_name):
            for r in chromo['fields']:
                if r['datastore_id'] == f['datastore_id'] and \
                        r.get('form_full_text_choices', False):
                    choice_fields[f['datastore_id']] = [{'value': k,
                                                         'label': k + ': ' + v}
                                                        for (k, v) in f['choices']]
            if f['datastore_id'] not in choice_fields:
                choice_fields[f['datastore_id']] = [{'value': k, 'label': v}
                                                    for (k, v) in f['choices']]

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
            post_data = parse_params(request.POST, ignore_keys=['save'] + pk_fields)

            if 'cancel' in post_data:
                return h.redirect_to(h.url_for(
                    controller='ckanext.recombinant.controller:UploadController',
                    action='preview_table',
                    resource_name=resource_name,
                    owner_org=rcomb['owner_org'],
                    ))

            data, err = clean_check_type_errors(
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
                        'errors': err,
                        })

            h.flash_notice(_(u'Record %s Updated') % u','.join(pk) )

            return h.redirect_to(h.url_for(
                controller='ckanext.recombinant.controller:UploadController',
                action='preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
                ))

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
                'errors': {},
                })

    def type_redirect(self, resource_name):
        orgs = h.organizations_available('read')

        if not orgs:
            abort(404, _('No organizations found'))
        try:
            chromo = get_chromo(resource_name)
        except RecombinantException:
            abort(404, _('Recombinant resource_name not found'))

        # custom business logic
        if is_sysadmin(c.user):
            return h.redirect_to(h.url_for('recombinant_resource',
                                      resource_name=resource_name, owner_org='tbs-sct'))
        return h.redirect_to(h.url_for('recombinant_resource',
                                  resource_name=resource_name, owner_org=orgs[0]['name']))

def clean_check_type_errors(post_data, fields, pk_fields, choice_fields):
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

