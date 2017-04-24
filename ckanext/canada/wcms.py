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
    or_,
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


# fetch all sub comments
def fetch_comments_by_id(thread):
    global _drupal_db

    if _drupal_db is None:
        return []

    comment_list = []
    ct = _drupal_db.drupal_comments_table.c

    try:
        stmt = select(
            [
                _drupal_db.drupal_comments_table
            ],
        ).where(
            or_(ct.thread == (thread + '/'),
                ct.thread.like(thread + '.%')
                )
        )

        for comment in stmt.execute():
            comment_body = clean_html(comment[3])
            comment_list.append({
                 'date': comment[0],
                 'thread': comment[2],
                 'comment_body': comment_body,
                 'user': comment[1]
            })
    except KeyError:
        # I can't figure out why this try...except is here, so lets log it
        # upstream and see if Sentry can tell us why.
        logging.exception('KeyError occured while pulling dataset comments.')
    return comment_list


# group comments by thread id, asc or desc; fetch parent thread if necessary
def comments_by_thread(comment_list, asc=True):
    res = []
    com_ids = [c['thread'] for c in comment_list]
    for com in comment_list:
        thread = com['thread']
        parent_id = thread.strip('/').partition('.')[0]
        if (parent_id + '/') not in com_ids:
            cs = fetch_comments_by_id(parent_id)
            for c in cs:
                if c['thread'] not in com_ids:
                    res.append(c)
                    com_ids.append(c['thread'])
    res += comment_list

    clist = {}  # key: thread_id,, value: [children, comment]

    def buildNode(parents, comment):
        root = clist
        node = None
        for id in parents:
            if root.get(id) is None:
                root[id] = [{}, None]
            node = root[id]
            root=root[id][0]
        node[1] =comment

    #now we have all comments with parent; build subtree, then sort by date
    #step1: build tree
    for c in res:
        thread = c['thread']
        c['parents'] = thread.strip('/').split('.')
        buildNode(c['parents'], c)

    def sortDict(d):
        ordered_d = sorted(d.items(), key=lambda x: x[0], reverse=(not asc))
        for k,v in ordered_d:
            if v[0]:
                v[0] = sortDict(v[0])
        return [v[1] for v in ordered_d]
    #step 2: sort
    return sortDict(clist)


def wcms_dataset_comments(request, c, pkg_id):
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
        sort_by = request.params.get('sort', 'time_descend')
        asc = sort_by=='time_ascend'

        stmt = select(
            [
                _drupal_db.drupal_comments_table
            ],
            limit=limit,
            offset=(page - 1) * limit,
            order_by=[_drupal_db.drupal_comments_table.c.thread.asc() if asc
                      else
                      _drupal_db.drupal_comments_table.c.thread.desc()]
        ).where(ct.pkg_id== pkg_id)
        for comment in stmt.execute():
            comment_body = clean_html(comment[3])
            comment_list.append({
                 'date': comment[0],
                 'thread': comment[2],
                 'comment_body': comment_body,
                 'user': comment[1]
            })
        comment_list = comments_by_thread(comment_list, asc)
        c.page = h.Page(
            collection=comment_list,
            page=page,
            url=pager_url,
            item_count=wcms_dataset_comment_count(pkg_id),
            items_per_page=limit
        )
        c.pagelimit = limit
        c.sort = sort_by
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


def wcms_dataset_comment_count(package_id):
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

    try:
        return int(count) if count else 0
    except ValueError:
        return 0
