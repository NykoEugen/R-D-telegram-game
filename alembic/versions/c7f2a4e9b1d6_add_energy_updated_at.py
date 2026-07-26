"""add_energy_updated_at

Revision ID: c7f2a4e9b1d6
Revises: b4d8e21f9c3a
Create Date: 2026-07-26 00:00:00.000000

Adds players.energy_updated_at, used by PlayerRepository.apply_energy_regen
to lazily regenerate energy based on elapsed time (Config.
ENERGY_REGENERATION_RATE per hour) instead of a background job.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f2a4e9b1d6'
down_revision = 'b4d8e21f9c3a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'players',
        sa.Column(
            'energy_updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('players', 'energy_updated_at')
