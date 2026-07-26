"""remove_legacy_scene_world_systems

Revision ID: b4d8e21f9c3a
Revises: 8ccfb7d41cb9
Create Date: 2026-07-26 00:00:00.000000

Drops the legacy scene-graph engine (scenes/actions/quests) and the legacy
region-exploration system (player_progress/exploration_sessions/
region_unlocks/player_stats/quest_proposals/player_reputation) — none of
these were ever wired into the live gameplay flow. Also drops the two dead
FK columns on players (current_scene_id/current_quest_id) and replaces
quest_progress with a YAML-content-backed schema (quest_id is now a plain
string key matching content in app/game/quests/, not a FK to the removed
quests table). The old quest_progress table had zero writers in the live
code, so it is safe to drop and recreate rather than migrate data.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b4d8e21f9c3a'
down_revision = '8ccfb7d41cb9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- legacy region-exploration system ---
    op.drop_index(op.f('ix_quest_proposals_id'), table_name='quest_proposals')
    op.drop_table('quest_proposals')

    op.drop_index(op.f('ix_player_reputation_id'), table_name='player_reputation')
    op.drop_table('player_reputation')

    op.drop_table('exploration_sessions')
    op.drop_table('region_unlocks')
    op.drop_table('player_stats')
    op.drop_table('player_progress')

    # --- old quest_progress (FK'd to legacy quests table) ---
    op.drop_index(op.f('ix_quest_progress_id'), table_name='quest_progress')
    op.drop_table('quest_progress')

    # --- dead FK columns on players (legacy scene/quest engine) ---
    op.drop_column('players', 'current_scene_id')
    op.drop_column('players', 'current_quest_id')

    # --- legacy scene-graph engine ---
    op.drop_index(op.f('ix_actions_id'), table_name='actions')
    op.drop_table('actions')

    op.drop_index(op.f('ix_scenes_scene_id'), table_name='scenes')
    op.drop_index(op.f('ix_scenes_id'), table_name='scenes')
    op.drop_table('scenes')

    op.drop_index(op.f('ix_quests_quest_id'), table_name='quests')
    op.drop_index(op.f('ix_quests_id'), table_name='quests')
    op.drop_table('quests')

    # --- new quest_progress: player-state only, quest_id is a YAML content key ---
    op.create_table(
        'quest_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('quest_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_objective_idx', sa.Integer(), nullable=False),
        sa.Column('obj_progress', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('repeat_count', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(), nullable=True),
        sa.Column('rewards_claimed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], name=op.f('fk_quest_progress_player_id_players')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_quest_progress')),
    )
    op.create_index(op.f('ix_quest_progress_id'), 'quest_progress', ['id'], unique=False)
    op.create_index(op.f('ix_quest_progress_quest_id'), 'quest_progress', ['quest_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quest_progress_quest_id'), table_name='quest_progress')
    op.drop_index(op.f('ix_quest_progress_id'), table_name='quest_progress')
    op.drop_table('quest_progress')

    op.create_table(
        'quests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quest_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quest_type', sa.String(length=50), nullable=False),
        sa.Column('is_repeatable', sa.Boolean(), nullable=False),
        sa.Column('max_repeats', sa.Integer(), nullable=True),
        sa.Column('level_requirement', sa.Integer(), nullable=False),
        sa.Column('required_flags', sa.JSON(), nullable=True),
        sa.Column('required_quests', sa.JSON(), nullable=True),
        sa.Column('objectives', sa.JSON(), nullable=True),
        sa.Column('experience_reward', sa.Integer(), nullable=False),
        sa.Column('coins_reward', sa.Integer(), nullable=False),
        sa.Column('items_reward', sa.JSON(), nullable=True),
        sa.Column('quest_data', sa.JSON(), nullable=True),
        sa.Column('start_scene_id', sa.String(length=100), nullable=True),
        sa.Column('end_scene_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_quests')),
    )
    op.create_index(op.f('ix_quests_id'), 'quests', ['id'], unique=False)
    op.create_index(op.f('ix_quests_quest_id'), 'quests', ['quest_id'], unique=True)

    op.create_table(
        'scenes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scene_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scene_type', sa.String(length=50), nullable=False),
        sa.Column('is_accessible', sa.Boolean(), nullable=False),
        sa.Column('level_requirement', sa.Integer(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('background_image', sa.String(length=500), nullable=True),
        sa.Column('music_track', sa.String(length=255), nullable=True),
        sa.Column('connected_scenes', sa.JSON(), nullable=True),
        sa.Column('required_flags', sa.JSON(), nullable=True),
        sa.Column('required_items', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_scenes')),
    )
    op.create_index(op.f('ix_scenes_id'), 'scenes', ['id'], unique=False)
    op.create_index(op.f('ix_scenes_scene_id'), 'scenes', ['scene_id'], unique=True)

    op.create_table(
        'actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scene_id', sa.Integer(), nullable=False),
        sa.Column('action_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('level_requirement', sa.Integer(), nullable=False),
        sa.Column('required_flags', sa.JSON(), nullable=True),
        sa.Column('required_items', sa.JSON(), nullable=True),
        sa.Column('cost_energy', sa.Integer(), nullable=False),
        sa.Column('cost_mana', sa.Integer(), nullable=False),
        sa.Column('effects', sa.JSON(), nullable=True),
        sa.Column('target_scene_id', sa.String(length=100), nullable=True),
        sa.Column('action_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], name=op.f('fk_actions_scene_id_scenes')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_actions')),
    )
    op.create_index(op.f('ix_actions_id'), 'actions', ['id'], unique=False)

    op.add_column('players', sa.Column('current_quest_id', sa.Integer(), nullable=True))
    op.add_column('players', sa.Column('current_scene_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f('fk_players_current_quest_id_quests'), 'players', 'quests', ['current_quest_id'], ['id']
    )
    op.create_foreign_key(
        op.f('fk_players_current_scene_id_scenes'), 'players', 'scenes', ['current_scene_id'], ['id']
    )

    op.create_table(
        'quest_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('quest_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_objective', sa.Integer(), nullable=False),
        sa.Column('progress_data', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('repeat_count', sa.Integer(), nullable=False),
        sa.Column('rewards_claimed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], name=op.f('fk_quest_progress_player_id_players')),
        sa.ForeignKeyConstraint(['quest_id'], ['quests.id'], name=op.f('fk_quest_progress_quest_id_quests')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_quest_progress')),
    )
    op.create_index(op.f('ix_quest_progress_id'), 'quest_progress', ['id'], unique=False)

    op.create_table(
        'player_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_level', sa.Integer(), nullable=False),
        sa.Column('total_experience', sa.Integer(), nullable=False),
        sa.Column('completed_quests', sa.JSON(), nullable=True),
        sa.Column('unlocked_regions', sa.JSON(), nullable=True),
        sa.Column('visited_locations', sa.JSON(), nullable=True),
        sa.Column('achievements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_player_progress_id'), 'player_progress', ['id'], unique=False)

    op.create_table(
        'exploration_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.String(), nullable=False),
        sa.Column('session_start', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('session_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('events_encountered', sa.JSON(), nullable=True),
        sa.Column('enemies_defeated', sa.JSON(), nullable=True),
        sa.Column('loot_obtained', sa.JSON(), nullable=True),
        sa.Column('experience_gained', sa.Integer(), nullable=True),
        sa.Column('gold_gained', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exploration_sessions_id'), 'exploration_sessions', ['id'], unique=False)

    op.create_table(
        'region_unlocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.String(), nullable=False),
        sa.Column('unlock_type', sa.String(), nullable=False),
        sa.Column('unlock_value', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_unlocked_by_default', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_id'),
    )
    op.create_index(op.f('ix_region_unlocks_id'), 'region_unlocks', ['id'], unique=False)

    op.create_table(
        'player_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_enemies_defeated', sa.Integer(), nullable=True),
        sa.Column('total_quests_completed', sa.Integer(), nullable=True),
        sa.Column('total_regions_explored', sa.Integer(), nullable=True),
        sa.Column('total_exploration_time', sa.Integer(), nullable=True),
        sa.Column('favorite_region', sa.String(), nullable=True),
        sa.Column('longest_exploration_session', sa.Integer(), nullable=True),
        sa.Column('total_gold_earned', sa.Integer(), nullable=True),
        sa.Column('total_experience_gained', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_player_stats_id'), 'player_stats', ['id'], unique=False)

    op.create_table(
        'player_reputation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('faction', sa.String(), nullable=False),
        sa.Column('reputation', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_player_reputation_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_reputation')),
    )
    op.create_index(op.f('ix_player_reputation_id'), 'player_reputation', ['id'], unique=False)

    op.create_table(
        'quest_proposals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('questgiver_name', sa.String(), nullable=False),
        sa.Column('quest_intro', sa.Text(), nullable=False),
        sa.Column('quest_description', sa.Text(), nullable=False),
        sa.Column('additional_info', sa.Text(), nullable=True),
        sa.Column('faction', sa.String(), nullable=True),
        sa.Column('reward_gold', sa.Integer(), nullable=True),
        sa.Column('reward_xp', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.Integer(), nullable=True),
        sa.Column('info_asked', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_quest_proposals_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_quest_proposals')),
    )
    op.create_index(op.f('ix_quest_proposals_id'), 'quest_proposals', ['id'], unique=False)
