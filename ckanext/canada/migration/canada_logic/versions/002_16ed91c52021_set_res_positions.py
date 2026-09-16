"""Fix resource positions not based on 0 index

Revision ID: 16ed91c52021
Revises: 0ef791477ff0
Create Date: 2026-02-04 16:21:56.703503

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '16ed91c52021'
down_revision = '0ef791477ff0'
branch_labels = None
depends_on = None


def _get_tables():
    engine = op.get_bind()
    inspector = sa.inspect(engine)
    return inspector.get_table_names(), engine


def upgrade():
    tables, engine = _get_tables()
    if 'resource' not in tables:
        raise Exception('resource database table does not exist')

    with engine.connect() as conn:
        query_string = """
            UPDATE resource SET position=0 WHERE state='deleted';"""

        conn.execute(sa.text(query_string))
        print('Set position=0 for deleted resources...')

        query_string = """
            WITH numbered AS (
                SELECT
                    id,
                    package_id,
                    position,
                    ROW_NUMBER() OVER (
                        PARTITION BY package_id
                        ORDER BY position
                    ) - 1 AS new_position
                FROM resource WHERE state='active'
            ),
            updated AS (
                UPDATE resource
                SET position=numbered.new_position
                FROM numbered
                WHERE resource.id = numbered.id
                AND resource.position != numbered.new_position
                RETURNING resource.package_id
            )
            SELECT DISTINCT package_id FROM updated;"""

        result = conn.execute(sa.text(query_string))

        updated_package_ids = [r[0] for r in result]
        total = len(updated_package_ids)
        if total == 0:
            print('Did not find any resources needing position updating...')
            return
        print('Updated %s packages. They will need to be reindex' % total)
        print(' ')
        for package_id in updated_package_ids:
            print(package_id)
        print(' ')
        print('DONE!')


def downgrade():
    pass
