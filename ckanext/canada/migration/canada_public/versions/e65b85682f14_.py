"""empty message

Revision ID: e65b85682f14
Revises: 0ef791477ff0
Create Date: 2025-11-19 15:19:17.479326

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e65b85682f14'
down_revision = '0ef791477ff0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("idx_only_one_active_email")
    print('Dropped "idx_only_one_active_email" index')
    op.create_index(
        "idx_only_one_active_email_no_case", "user",
        [sa.func.lower(sa.Column('email')), "state"],
        unique=True, postgresql_where=sa.text('"user".state=\'active\''))
    print('Created "idx_only_one_active_email_no_case" index')
    pass


def downgrade():
    op.drop_index("idx_only_one_active_email_no_case")
    print('Dropped "idx_only_one_active_email_no_case" index')
    op.create_index(
        "idx_only_one_active_email", "user", ["email", "state"],
        unique=True, postgresql_where=sa.text('"user".state=\'active\''))
    print('Created "idx_only_one_active_email" index')
    pass
