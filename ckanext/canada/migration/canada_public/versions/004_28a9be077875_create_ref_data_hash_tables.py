"""empty message

Revision ID: 28a9be077875
Revises: 015d2fdd075f
Create Date: 2026-06-09 16:25:19.100497

"""
from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision = '28a9be077875'
down_revision = '015d2fdd075f'
branch_labels = None
depends_on = None


def _get_tables():
    engine = op.get_bind()
    inspector = sa.inspect(engine)
    return inspector.get_table_names()


def upgrade():
    tables = _get_tables()
    if "ref_data" in tables:
        print('ref_data database table already exists')
        return
    op.create_table(
        "ref_data",
        sa.Column("table_name", sa.Unicode, primary_key=True),
        sa.Column("last_sync", sa.DateTime,
                  nullable=False,
                  default=datetime.datetime.now(datetime.timezone.utc)),
        sa.Column("file_hash", sa.Unicode, nullable=False),
    )
    print('ref_data database table created')
    pass


def downgrade():
    tables = _get_tables()
    if "ref_data" not in tables:
        print('ref_data database table not present')
        return
    op.drop_table("ref_data")
    print('ref_data database table deleted')
    pass
