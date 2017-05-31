# -*- coding: utf-8 -*-
import datetime
from urllib import urlencode

import requests
from pylons import config
from lxml.html.clean import clean_html

import ckan.lib.helpers as h


def wcms_configure(*args, **kwargs):
    pass


def wcms_inventory_votes():
    return {}


def wcms_dataset_comments(request, c, pkg_id):
    # [{
    # 'date': ...,
    # 'thread': ...,
    # 'comment_body': ...,
    # 'user': ...
    # }]
    url = config.get('ckanext.canada.drupal_url')
    if not url:
        return []

    r = requests.get(
        url + '/jsonapi/external_comment/external_comment',
        params={
            '_format': 'api_json',
            'filter[ckan][condition][path]': 'commented_external_entity',
            'filter[ckan][condition][value]': 'ckan-{0}'.format(
                pkg_id
            )
        },
        auth=(
            config.get('ckanext.canada.drupal_user'),
            config.get('ckanext.canada.drupal_pass')
        )
    )

    j = r.json()

    comment_list = [{
        'date': h.time_ago_from_timestamp(
            datetime.datetime.utcfromtimestamp(
                rec['attributes']['changed']
            )
        ),
        'thread': rec['attributes']['thread'],
        'user': rec['attributes']['name'],
        'comment_body': clean_html(
            rec['attributes']['comment_body']['value']
        )
    } for rec in j['data']]

    sort_by = request.params.get('sort', 'time_descend')
    asc = sort_by == 'time_ascend'

    params_nopage = [
        (k, v) for k, v in request.params.items()
        if k != 'page'
    ]

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params, pkg_id)

    cbt = comments_by_thread(comment_list, asc),

    c.page = h.Page(
        collection=cbt,
        page=1,
        url=pager_url,
        item_count=len(comment_list),
        items_per_page=len(comment_list)
    )
    c.sort = sort_by

    return cbt[0]


def wcms_dataset_rating(package_id):
    return 0


def wcms_dataset_comment_count(package_id):
    url = config.get('ckanext.canada.drupal_url')
    if not url:
        return []

    r = requests.get(
        url + '/jsonapi/external_comment/external_comment',
        params={
            '_format': 'api_json',
            'filter[ckan][condition][path]': 'commented_external_entity',
            'filter[ckan][condition][value]': 'ckan-{0}'.format(
                package_id
            )
        },
        auth=(
            config.get('ckanext.canada.drupal_user'),
            config.get('ckanext.canada.drupal_pass')
        )
    )

    j = r.json()

    return len(j['data'])


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
