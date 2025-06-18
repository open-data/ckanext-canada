"""empty message

Revision ID: 3918d33c5c7f
Revises: 0ef791477ff0
Create Date: 2025-06-18 17:16:49.755578

"""
from alembic import op
import sqlalchemy as sa

import datetime


# revision identifiers, used by Alembic.
revision = '3918d33c5c7f'
down_revision = '0ef791477ff0'
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
    # TODO: set private=False where ready_to_publish=true and imso_approval=true and portal_release_date!=null
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
