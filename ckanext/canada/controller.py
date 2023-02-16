# -*- coding: utf-8 -*-
import json

import webhelpers.feedgenerator

from ckan.lib.base import model
from ckan.controllers.api import NotFound
from ckan.lib.helpers import (
    date_str_to_datetime,
    url,
)
from ckan.controllers.feed import (
    FeedController,
    _package_search,
    _create_atom_id,
    _FixedAtom1Feed
)
from ckan.logic import  NotFound

from ckan.plugins.toolkit import _, config

from ckantoolkit import (
    c,
    h,
    response,
    abort,
    get_action,
    )


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

    def dataset(self, pkg_id):
        try:
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'auth_user_obj': c.userobj}
            get_action('package_show')(context,
                                        {'id': pkg_id})
        except NotFound:
            abort(404, _('Dataset not found'))

        data_dict, params = self._parse_url_params()

        data_dict['fq'] = '{0}:"{1}"'.format('id', pkg_id)

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action='dataset',
                                                id=pkg_id)

        feed_url = self._feed_url(params,
                                  controller='feed',
                                  action='dataset',
                                  id=pkg_id)

        alternate_url = self._alternate_url(params, id=pkg_id)

        return self.output_feed(
            results,
            feed_title=_(u'Open Government Dataset Feed'),
            feed_description='',
            feed_link=alternate_url,
            feed_guid=_create_atom_id(
                u'/feeds/dataset/{0}.atom'.format(pkg_id)),
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
                link=h.url_for('package.read', id=pkg['id']),
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

