"""Drop the package_sync table.

It is no longer needed in combined Portal & Registry instances.

Revision ID: 480855025fc7
Revises: 015d2fdd075f
Create Date: 2026-02-18 15:38:38.950477

"""
from alembic import op
import sqlalchemy as sa

import datetime


# revision identifiers, used by Alembic.
revision = '480855025fc7'
down_revision = '015d2fdd075f'
branch_labels = None
depends_on = None


def _get_tables():
    engine = op.get_bind()
    inspector = sa.inspect(engine)
    return inspector.get_table_names()


def upgrade():
    tables = _get_tables()
    if "package_sync" not in tables:
        print('package_sync database table not present')
        return
    op.drop_table("package_sync")
    print('package_sync database table deleted')
    pass


def downgrade():
    tables = _get_tables()
    if "package_sync" in tables:
        print('package_sync database table already exists')
        return
    op.create_table(
        "package_sync",
        sa.Column("package_id", sa.Unicode, primary_key=True),
        sa.Column("last_run", sa.DateTime,
                  nullable=False,
                  default=datetime.datetime.now(datetime.timezone.utc)),
        sa.Column("last_successful_sync", sa.DateTime, nullable=True),
        sa.Column("error_on", sa.Unicode, nullable=True),
        sa.Column("error", sa.Unicode, nullable=True),
    )
    print('package_sync database table created')
    pass
