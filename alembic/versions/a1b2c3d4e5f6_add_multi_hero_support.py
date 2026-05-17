"""add_multi_hero_support

Revision ID: a1b2c3d4e5f6
Revises: cd3f491d571f
Create Date: 2026-05-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'cd3f491d571f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add slot and is_active columns
    op.add_column('players', sa.Column('slot', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('players', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Drop the unique constraint on user_id
    op.drop_constraint('uq_players_user_id', 'players', type_='unique')


def downgrade() -> None:
    # Restore unique constraint (this will fail if there are duplicate user_ids)
    op.create_unique_constraint('uq_players_user_id', 'players', ['user_id'])

    op.drop_column('players', 'is_active')
    op.drop_column('players', 'slot')
