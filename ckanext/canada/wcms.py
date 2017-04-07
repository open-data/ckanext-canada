# -*- coding: utf-8 -*-
import logging
from urllib import urlencode
from lxml.html.clean import clean_html

from sqlalchemy import (
    create_engine,
    Column,
    MetaData,
    Table,
    types,
    select,
    bindparam,
    and_,
    func
)
import ckan.lib.helpers as h

# SQLalchemy MetaData object for the Drupal WCMS.
_drupal_db = None

def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v))
            for k, v in params]

def search_url(params, package_id):
    url = h.url_for(controller='package', action='read', id=package_id)
    return url + u'?' + urlencode(params)

class _DrupalDatabase(object):
    # Class to encapsulate the SQLAlchemy tables of Drupal database and give us
    # access to the user comments and ratings for CKAN datasets

    log = logging.getLogger(__name__)
    drupal_comments_table = None
    drupal_comments_count_table = None
    drupal_ratings_table = None

    def __init__(self, metadata):
        self._metadata = metadata

        self.drupal_comments_table = Table(
            'opendata_package_v',
            self._metadata,
            Column(
                'changed',
                types.UnicodeText,
                primary_key=True,
                nullable=False
            ),
            Column('name', types.Unicode(60)),
            Column('thread', types.Unicode(255)),
            Column('comment_body_value', types.UnicodeText),
            Column('language', types.Unicode(12)),
            Column('pkg_id', types.UnicodeText)
        )

        self.drupal_comments_count_table = Table(
            'opendata_package_count_v',
            self._metadata,
            Column('count', types.Integer),
            Column('pkg_id', types.UnicodeText),
            Column('language', types.Unicode(12)),
        )

        self.drupal_ratings_table = Table(
            'opendata_package_rating_v',
            self._metadata,
            Column('rating', types.Float),
            Column('pkg_id', types.UnicodeText)
        )


def wcms_configure(drupal_url):
    global _drupal_db

    required_tables = (
        'opendata_package_v',
        'opendata_package_count_v',
        'opendata_package_rating_v'
    )

    # Load just once
    if _drupal_db is None:
        engine = create_engine(drupal_url)
        metadata = MetaData(bind=engine)

        for rq_table in required_tables:
            if not engine.dialect.has_table(engine, rq_table):
                logging.error(
                    'Required drupal table {0!r} missing.'.format(
                        rq_table
                    )
                )
                _drupal_db = None
                return

        _drupal_db = _DrupalDatabase(metadata)


def wcms_dataset_comments(request, c, pkg_id, lang):
    """
    Retrieve the comments for this dataset that have been saved in the Drupal
    database
    """
    global _drupal_db

    if _drupal_db is None:
        return []

    comment_list = []
    ct = _drupal_db.drupal_comments_table.c

    try:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, pkg_id)

        page = int(request.params.get('page', 1))
        limit = min(100, int(request.params.get('pagelimit', 50)))

        stmt = select(
            [
                _drupal_db.drupal_comments_table
            ],
            and_(
                ct.pkg_id == bindparam('pkg_id'),
                ct.language == bindparam('language')
            ),
            limit = limit,
            offset = (page - 1) * limit,
            order_by=[_drupal_db.drupal_comments_table.c.thread.desc()]
        )

        for comment in stmt.execute(pkg_id=pkg_id, language=lang):
            comment_body = clean_html(comment[3])
            comment_list.append({
                 'date': comment[0],
                 'thread': comment[2],
                 'comment_body': comment_body,
                 'user': comment[1]
            })
        c.page = h.Page(
            collection=comment_list,
            page=page,
            url=pager_url,
            item_count=wcms_dataset_comment_count(pkg_id, lang),
            items_per_page=limit
        )
        c.pagelimit = limit
    except KeyError:
        # I can't figure out why this try...except is here, so lets log it
        # upstream and see if Sentry can tell us why.
        logging.exception('KeyError occured while pulling dataset comments.')

    return comment_list


def wcms_dataset_rating(package_id):
    """
    Retrieve the average of the user's 5 star ratings of the dataset
    """
    global _drupal_db
    rating = None

    if _drupal_db is None:
        return 0

    ct = _drupal_db.drupal_ratings_table.c

    try:
        stmt = select(
            [
                _drupal_db.drupal_ratings_table
            ],
            whereclause=ct.pkg_id == bindparam('pkg_id')
        )

        row = stmt.execute(pkg_id=package_id).fetchone()
        if row:
            rating = row[0]
    except KeyError:
        # I can't figure out why this try...except is here, so lets log it
        # upstream and see if Sentry can tell us why.
        logging.exception('KeyError occured while pulling dataset ratings.')

    return int(0 if rating is None else rating)


def wcms_dataset_comment_count(package_id, lang=''):
    """
    Get a count of the number of comments for the dataset. This count is
    displayed in a seperate field on the dataset page
    """
    global _drupal_db
    count = 0

    if _drupal_db is None:
        return 0

    ct = _drupal_db.drupal_comments_count_table.c

    try:
        if lang:
            stmt = select(
                [
                    _drupal_db.drupal_comments_count_table
                ],
                and_(
                    ct.pkg_id == bindparam('pkg_id'),
                    ct.language == bindparam('language')
                )
            )
            row = stmt.execute(pkg_id=package_id, language=lang).fetchone()
        else:
            stmt = select(
                [
                    func.sum(_drupal_db.drupal_comments_count_table.c.count)
                ],
                and_(
                    ct.pkg_id == bindparam('pkg_id'),
                )
            )
            row = stmt.execute(pkg_id=package_id).fetchone()

        if row:
            count = row[0]
    except KeyError:
        # I can't figure out why this try...except is here, so lets log it
        # upstream and see if Sentry can tell us why.
        logging.exception('KeyError occured while pulling comment count.')

    return count
