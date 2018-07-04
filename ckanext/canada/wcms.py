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
def dataset_rating(package_id, entity_prefix='ckan-'):
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
            'filter[ckan][condition][value]': entity_prefix + package_id,
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


def dataset_rating_obd(package_id):
    return dataset_rating(package_id, 'ckan_obd-')


def search_url(params, package_id):
    url = h.url_for(controller='package', action='read', id=package_id)
    return url + u'?' + urlencode(params)
