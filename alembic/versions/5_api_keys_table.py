"""Alembic migration: Add API keys table for authentication."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5_api_keys'
down_revision: Union[str, None] = '4_committee_meetings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_keys table for API authentication."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'api_keys' not in existing_tables:
        op.create_table(
            'api_keys',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('key_hash', sa.String(256), nullable=False, unique=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('rate_limit_requests', sa.Integer(), nullable=False, server_default='1000'),
            sa.Column('rate_limit_window_seconds', sa.Integer(), nullable=False, server_default='3600'),
            sa.Column('created_by', sa.String(200), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('requests_count', sa.Integer(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('key_hash', name='uq_api_key_hash'),
        )
        
        # Create indexes for common queries
        op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
        op.create_index('idx_api_keys_is_active', 'api_keys', ['is_active'])
        op.create_index('idx_api_keys_created_at', 'api_keys', ['created_at'])
        op.create_index('idx_api_keys_expires_at', 'api_keys', ['expires_at'])
        op.create_index(
            'idx_api_keys_active_expires',
            'api_keys',
            ['is_active', 'expires_at']
        )


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_table('api_keys', if_exists=True)
