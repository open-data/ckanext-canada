"""Create idx_package_resource_unique_position index
to make resource positions unique per package.

Revision ID: 015d2fdd075f
Revises: 16ed91c52021
Create Date: 2026-02-10 17:08:22.081916

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015d2fdd075f'
down_revision = '16ed91c52021'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_package_resource_unique_position", "resource",
        [sa.Column('package_id'), sa.Column('position')],
        unique=True, postgresql_where=sa.text('"resource".state=\'active\''))
    print('Created "idx_package_resource_unique_position" index')


def downgrade():
    op.drop_index("idx_package_resource_unique_position")
    print('Dropped "idx_package_resource_unique_position" index')
