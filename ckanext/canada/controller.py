# -*- coding: utf-8 -*-
import json
import socket
from logging import getLogger
import webhelpers.feedgenerator
from webob.exc import HTTPFound
from pytz import timezone, utc

import pkg_resources
import lxml.etree as ET
import lxml.html as html
import unicodecsv
import codecs
from ckan.lib.base import model, redirect
from ckan.logic import schema
from ckan.controllers.user import UserController
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

from ckanext.canada.helpers import normalize_strip_accents
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
    )


from ckanapi import LocalCKAN, NotAuthorized
from ckanext.recombinant.datatypes import canonicalize

int_validator = get_validator('int_validator')

ottawa_tz = timezone('America/Montreal')


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

    def registry_menu(self):
        return render("menu.html")

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
            # Fall back to using English if no local langauge could be found.
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

            # We don't actaully want the FAQ headers to be headings, so strip
            # the tags and just leave the text.
            faq_section.drop_tag()

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
        sort_by_num = int(request.params['order[0][column]'])
        sort_order = ('desc' if request.params['order[0][dir]'] == 'desc'
                      else 'asc'
                      )

        chromo = h.recombinant_get_chromo(resource_name)
        lc = LocalCKAN(username=c.user)
        unfiltered_response = lc.action.datastore_search(
            resource_id=resource_id,
            limit=1,
        )

        cols = [f['datastore_id'] for f in chromo['fields']]
        sort_str = cols[sort_by_num] + ' ' + sort_order

        response = lc.action.datastore_search(
            q=search_text,
            resource_id=resource_id,
            offset=offset,
            limit=limit,
            sort=sort_str
        )

        return json.dumps({
            'draw': draw,
            'iTotalRecords': unfiltered_response.get('total', 0),
            'iTotalDisplayRecords': response.get('total', 0),
            'aaData': [
                [datatablify(row.get(colname, u''), colname) for colname in cols]
                for row in response['records']
            ],
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

    def data_dictionary(self, pd_file):
        name, dot, ext = pd_file.partition('.')
        if ext != 'csv':
            abort(404, _('Resource not found'))
        chromo = h.recombinant_get_chromo(name)
        if not chromo:
            abort(404, _('Resource not found'))

        csv_dict = [(_('Field Name'), _('Description'))]
        for f in chromo['fields']:
            csv_dict.append((f['datastore_id'],
                h.recombinant_language_text(f['label'])))
        csv_dict.append(('owner_org',_('owner organization') ))
        csv_dict.append(('owner_org_title',_('owner organization title')))

        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = (
            'inline; filename="{0}"'.format(pd_file))
        response.write(codecs.BOM_UTF8)
        out = unicodecsv.writer(response)
        for row in csv_dict:
            out.writerow([unicode(col).encode('utf-8') for col in row])
        return


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
        return h.date_str_to_datetime(v).replace(tzinfo=utc).astimezone(
            ottawa_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
    return unicode(v)


class CanadaDatasetController(PackageController):
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
            h.flash_error(_('Login failed. Bad username or password.'))
            return h.redirect_to(
                controller='user',
                action='login', locale=lang
            )

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

        if c.user and not data:
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
        for key, package_id in request.str_POST.iteritems():
            if key == 'publish':
                lc.action.package_patch(
                    id=package_id,
                    portal_release_date=publish_date,
                )

        # return us to the publishing interface
        redirect(h.url_for('ckanadmin_publish'))


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
                    u'New data.gc.ca Registry Account Created / Nouveau compte'
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

    def create_travela(self, id, resource_id):
        lc = LocalCKAN(username=c.user)
        pkg = lc.action.package_show(id=id)
        res = lc.action.resource_show(id=resource_id)
        org = lc.action.organization_show(id=pkg['owner_org'])
        dataset = lc.action.recombinant_show(
            dataset_type='travela', owner_org=org['name'])

        chromo = h.recombinant_get_chromo('travela')
        data = {}
        data_prev = {}
        form_data = {}
        for f in chromo['fields']:
            dirty = request.params.getone(f['datastore_id'])
            data[f['datastore_id']] = canonicalize(dirty, f['datastore_type'])
            if f['datastore_id'] + '_prev' in request.params:
                 data_prev[f['datastore_id']] = request.params.getone(f['datastore_id'] + '_prev')
                 form_data[f['datastore_id'] + '_prev'] = data_prev[f['datastore_id']]

        form_data.update(data)

        def error(errors):
            return render('recombinant/resource_edit.html',
                extra_vars={
                    'create_errors': errors,
                    'create_data': form_data,
                    'delete_errors': [],
                    'dataset': dataset,
                    'resource': res,
                    'organization': org,
                    'filters': {},
                    'action': 'edit'})

        try:
            year = int_validator(data['year'], None)
        except Invalid:
            year = None

        if not year:
            return error({'year': [_(u'Invalid year')]})

        response = lc.action.datastore_search(resource_id=resource_id,
            filters={'year': data['year']})
        if response['records']:
            return error({'year': [_(u'Data for this year has already been entered')]})

        response = lc.action.datastore_search(resource_id=resource_id,
            filters={'year': year - 1})
        if response['records']:
            prev = response['records'][0]
            errors = {}
            for p in data_prev:
                if prev[p] != data_prev[p]:
                    errors[p + '_prev'] = [_(u'Does not match previous data "%s"') % prev[p]]
            if errors:
                return error(errors)
        else:
            lc.action.datastore_upsert(resource_id=resource_id,
                method='insert',
                records=[dict(data_prev, year=year - 1)])
            h.flash_success(_("Record for %d added.") % (year - 1))

        lc.action.datastore_upsert(resource_id=resource_id,
            method='insert',
            records=[data])

        h.flash_success(_("Record for %d added.") % year)

        redirect(h.url_for(
            controller='ckanext.recombinant.controller:UploadController',
            action='preview_table',
            resource_name=res['name'],
            owner_org=org['name'],
            ))
