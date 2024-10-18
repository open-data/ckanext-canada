"""empty message

Revision ID: 0ef791477ff0
Revises:
Create Date: 2024-10-18 18:20:50.040861

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ef791477ff0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from ckanext.canada.model import PackageSync
    if PackageSync.__table__.exists():
        print('%s database table already exists' % PackageSync.__tablename__)
        return
    PackageSync.__table__.create()
    print('%s database table created' % PackageSync.__tablename__)
    pass


def downgrade():
    from ckanext.canada.model import PackageSync
    if not PackageSync.__table__.exists():
        print('%s database table not present' % PackageSync.__tablename__)
        return
    PackageSync.__table__.drop()
    print('%s database table deleted' % PackageSync.__tablename__)
    pass
