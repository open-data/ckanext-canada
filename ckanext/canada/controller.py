import logging
import json
from ckan.lib.base import (BaseController, c, render, model, request, h, g,
    response)
from ckan.logic import get_action, NotAuthorized, check_access
from ckan.lib.helpers import Page, url_for, date_str_to_datetime, url
from ckan.controllers.feed import (FeedController, _package_search,
    _create_atom_id, _FixedAtom1Feed)
from ckan.lib import i18n

from ckanext.canada.helpers import normalize_strip_accents
from pylons.i18n import _
from pylons import config, session
import webhelpers.feedgenerator

class CanadaController(BaseController):
    def view_guidelines(self):
        return render('guidelines.html')

    def view_help(self):
        return render('help.html')

    def view_new_user(self):
        return render('newuser.html')

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

    def logged_in(self):
        # we need to set the language via a redirect
        lang = session.pop('lang', None)
        session.save()

        # we need to set the language explicitly here or the flash
        # messages will not be translated.
        i18n.set_lang(lang)

        if c.user:
            context = None
            data_dict = {'id': c.user}

            user_dict = get_action('user_show')(context, data_dict)

            h.flash_success(_("<p><strong>Note</strong></p>"
                "<p>%s is now logged in</p>") %
                user_dict['display_name'], allow_html=True)
            return h.redirect_to(controller='package',
                action='search', locale=lang)
        else:
            err = _('Login failed. Bad username or password.')
            return self.login(error=err)

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

        return self.output_feed(results,
            feed_title=_(u'Open Government'),
            feed_description=_(u'Recently created or '
            'updated datasets on %s') % g.site_title,
            feed_link=alternate_url,
            feed_guid=_create_atom_id(
            u'/feeds/dataset.atom'),
            feed_url=feed_url,
            navigation_urls=navigation_urls)

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
            def lx(x): return x + '_fra'
        else:
            def lx(x): return x

        for pkg in results:
            feed.add_item(
                title=pkg.get(lx('title'), ''),
                link=self.base_url + url(str(
                        '/api/action/package_show?id=%s' % pkg['name'])),
                description=pkg.get(lx('notes'), ''),
                updated=date_str_to_datetime(pkg.get('metadata_modified')),
                published=date_str_to_datetime(pkg.get('metadata_created')),
                unique_id=_create_atom_id(u'/dataset/%s' % pkg['id']),
                author_name=pkg.get('author', ''),
                author_email=pkg.get('author_email', ''),
                categories=''.join(e['value']
                    for e in pkg.get('extras',[])
                    if e['key'] == lx('keywords')).split(','),
                enclosure=webhelpers.feedgenerator.Enclosure(
                    self.base_url + url(str(
                        '/api/action/package_show?id=%s' % pkg['name'])),
                    unicode(len(json.dumps(pkg))),   # TODO fix this
                    u'application/json')
            )
        response.content_type = feed.mime_type
        return feed.writeString('utf-8')
