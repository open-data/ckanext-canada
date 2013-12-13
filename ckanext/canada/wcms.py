from lxml.html.clean import clean_html
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import types
from sqlalchemy import select, bindparam, and_
import logging

# SQLalchemy MetaData object for the Drupal WCMS.
_metadata = None

# Class to encapsulate the SQLAlchemy tables of Drupal database and give us access to the
# user comments and ratings for CKAN datasets
class _DrupalDatabase:
    global _metadata
    log = logging.getLogger(__name__)
    drupal_comments_table = None
    drupal_comments_count_table = None
    drupal_ratings_table = None

    def define_drupal_comments_table(self):

        self.drupal_comments_table = Table('opendata_package_v', _metadata,
            Column('changed',types.UnicodeText, primary_key=True, nullable=False),
            Column('name', types.Unicode(60)),
            Column('thread', types.Unicode(255)),
            Column('comment_body_value', types.UnicodeText),
            Column('language', types.Unicode(12)),
            Column('pkg_id', types.UnicodeText))

        self.drupal_comments_count_table = Table('opendata_package_count_v', _metadata,
            Column('count', types.Integer),
            Column('pkg_id', types.UnicodeText))

        self.drupal_ratings_table = Table('opendata_package_rating_v', _metadata,
            Column('rating', types.Float),
            Column('pkg_id', types.UnicodeText))


_drupal_db = None

def wcms_configure(drupal_url):
    global _drupal_db, _metadata
    # Load just once
    if _metadata is None:
        _drupal_db = _DrupalDatabase()
        _metadata = MetaData(drupal_url)
        _drupal_db.define_drupal_comments_table()

# Retrieve the comments for this dataset that have been saved in the Drupal database
def wcms_dataset_comments(pkg_id, lang):
    global _drupal_db
    comment_list = []
    try:
        if (_drupal_db is not None):
            where_clause = []
            clause_1 = _drupal_db.drupal_comments_table.c.pkg_id == bindparam('pkg_id')
            where_clause.append(clause_1)
            clause_2 = _drupal_db.drupal_comments_table.c.language == bindparam('language')
            where_clause.append(clause_2)
            and_clause = and_(*where_clause)
            stmt = select([_drupal_db.drupal_comments_table], and_clause,
                          order_by=[_drupal_db.drupal_comments_table.c.thread])

            for comment in stmt.execute(pkg_id=pkg_id, language=lang):
                 comment_body = clean_html(comment[3])
                 comment_list.append({'date': comment[0], 'thread': comment[2], 'comment_body': comment_body,
                                      'user': comment[1]})


    except KeyError:
        pass

    return comment_list

# Retrieve the average of the user's 5 star ratings of the dataset
def wcms_dataset_rating(package_id):
    global _drupal_db
    rating = None
    try:

        if _drupal_db is not None:
            stmt = select([_drupal_db.drupal_ratings_table],
                          whereclause=_drupal_db.drupal_ratings_table.c.pkg_id==bindparam('pkg_id'))
            row = stmt.execute(pkg_id=package_id).fetchone()
            if row:
                rating = row[0]

    except KeyError:
        pass
    return int(0 if rating is None else rating)

# Get a count of the number of comments for the dataset. This count is displayed in a seperate field on the
# dataset page
def wcms_dataset_comment_count(package_id):
    global _drupal_db
    count = 0

    try:

        if _drupal_db is not None:
            stmt = select([_drupal_db.drupal_comments_count_table],
                          whereclause=_drupal_db.drupal_comments_count_table.c.pkg_id==bindparam('pkg_id'))
            row = stmt.execute(pkg_id=package_id).fetchone()
            if row:
                count = row[0]

    except KeyError:
       pass
    return count