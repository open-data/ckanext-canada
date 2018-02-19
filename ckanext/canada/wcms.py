# -*- coding: utf-8 -*-
import logging
import datetime
from urllib import urlencode
from functools import wraps

import requests
from pylons import config
from lxml.html.clean import clean_html
from pytz import utc

import ckan.lib.helpers as h


logger = logging.getLogger(__name__)


def inventory_votes():
    return {}


def never_ever_fail(default=None):
    def _never_ever_fail(f):
        @wraps(f)
        def _f(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:
                logger.exception('Failed during a call to wcms')
                if callable(default):
                    return default()
                return default
        return _f
    return _never_ever_fail



@never_ever_fail(default=0)
def dataset_rating(package_id):
    """
    Retrieve the average of the user's 5 star ratings of the dataset
    """
    url = config.get('ckanext.canada.drupal_url')
    if not url:
        return 0

    r = requests.get(
        url + '/jsonapi/vote_result/vote_result',
        params={
            '_format': 'api_json',
            'filter[ckan][condition][path]': 'entity_id',
            'filter[ckan][condition][value]': 'ckan-' + package_id,
            'filter[group][group][conjunction]': 'OR',
            'filter[avg][condition][path]': 'function',
            'filter[avg][condition][value]': 'vote_average',
            'filter[avg][condition][memberOf]': 'group',
        },
        auth=(
            config.get('ckanext.canada.drupal_user'),
            config.get('ckanext.canada.drupal_pass')
        )
    )

    j = r.json()

    try:
        d = j['data']
    except KeyError:
        return 0

    for entry in d:
        if entry['attributes']['function'] == 'vote_average':
            return int(entry['attributes']['value']+0.5)
    else:
        return 0


@never_ever_fail(default=0)
def dataset_comment_count(package_id):
    url = config.get('ckanext.canada.drupal_url')
    if not url:
        return 0

    r = requests.get(
        url + '/jsonapi/external_comment/external_comment',
        params={
            '_format': 'api_json',
            'filter[ckan][condition][path]': 'commented_external_entity',
            'filter[ckan][condition][value]': 'ckan-{0}'.format(
                package_id
            ),
            'filter[status-filter][condition][path]': 'status',
            'filter[status-filter][condition][value]': '1'
        },
        auth=(
            config.get('ckanext.canada.drupal_user'),
            config.get('ckanext.canada.drupal_pass')
        )
    )

    j = r.json()

    return len(j.get('data', []))


@never_ever_fail(default=dict)
def comments_by_thread(comment_list, asc=True):
    res = []
    res += comment_list

    clist = {}  # key: thread_id,, value: [children, comment]

    def buildNode(parents, comment):
        root = clist
        node = None
        for id in parents:
            if root.get(id) is None:
                root[id] = [{}, None]
            node = root[id]
            root = root[id][0]
        node[1] = comment

    for c in res:
        thread = c['thread']
        c['parents'] = thread.strip('/').split('.')
        buildNode(c['parents'], c)

    def sortDict(d, depth):
        ordered_d = sorted(
            d.items(),
            key=lambda x: x[0],
            reverse=(not asc and depth == 0)
        )
        for k, v in ordered_d:
            if v[0]:
                v[0] = sortDict(v[0], depth+1)
        return [v[1] for v in ordered_d]
    return sortDict(clist, 0)


def search_url(params, package_id):
    url = h.url_for(controller='package', action='read', id=package_id)
    return url + u'?' + urlencode(params)
