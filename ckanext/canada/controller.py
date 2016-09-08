# -*- coding: utf-8 -*-
import json
import webhelpers.feedgenerator

from ckan.lib.base import (
    BaseController,
    c,
    render,
    model,
    request,
    h,
    response,
    abort,
    redirect
)
from ckan.logic import get_action, check_access, schema
from ckan.controllers.user import UserController
from ckan.authz import is_sysadmin
from ckan.lib.helpers import Page, date_str_to_datetime, url
from ckan.controllers.feed import (
    FeedController,
    _package_search,
    _create_atom_id,
    _FixedAtom1Feed
)
from ckan.lib import i18n
from ckan.controllers.package import PackageController

from ckanext.canada.helpers import normalize_strip_accents
from pylons.i18n import _
from pylons import config, session

from ckanapi import LocalCKAN, NotAuthorized


class CanadaController(BaseController):
    def home(self):
        if not c.user:
            h.redirect_to(controller='user', action='login')

        is_new = not h.check_access('package_create')

        if is_sysadmin(c.user) or is_new:
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
        return render('help.html')

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

    def datatable(self, resource_id):
        draw = int(request.params['draw'])
        search_text = unicode(request.params['search[value]'])
        offset = int(request.params['start'])
        limit = int(request.params['length'])
        sort_by_num = int(request.params['order[0][column]'])
        sort_order = ('desc' if request.params['order[0][dir]'] == 'desc'
                      else 'asc'
                      )

        lc = LocalCKAN(username=c.user)

        unfiltered_response = lc.action.datastore_search(
            resource_id=resource_id,
            limit=1,
        )

        cols = [f['id'] for f in unfiltered_response['fields']][1:]
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
                [row[colname] for colname in cols]
                for row in response['records']
            ],
        })


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

            if not h.check_access('package_create'):
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
            uc = UserController()
            return uc._save_new(context)

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
        return redirect('/')


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

        if c.language == 'fr':
            def lx(x):
                return x + '_fra'
        else:
            def lx(x):
                return x

        for pkg in results:
            feed.add_item(
                title=pkg.get(lx('title'), ''),
                link=self.base_url + url(str(
                    '/api/action/package_show?id=%s' % pkg['name'])
                ),
                description=pkg.get(lx('notes'), ''),
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
        return 'info'

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
