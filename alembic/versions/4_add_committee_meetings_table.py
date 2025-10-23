"""add committee_meetings table

Revision ID: 4_committee_meetings
Revises: 3_personalization
Create Date: 2025-10-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '4_committee_meetings'
down_revision: Union[str, None] = '3_personalization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add committee_meetings table."""
    
    # Get connection to check existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create committee_meetings table (if not exists)
    if 'committee_meetings' not in existing_tables:
        op.create_table(
            'committee_meetings',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('committee_id', sa.Integer(), nullable=False, comment='Foreign key to committees.id'),
            sa.Column('meeting_number', sa.Integer(), nullable=False, comment='Meeting number within session'),
            sa.Column('parliament', sa.Integer(), nullable=False, comment='Parliament number', index=True),
            sa.Column('session', sa.Integer(), nullable=False, comment='Session number', index=True),
            sa.Column('meeting_date', sa.DateTime(), nullable=False, comment='Date of meeting', index=True),
            sa.Column('time_of_day', sa.String(50), nullable=True, comment='Time of day (e.g., morning, afternoon)'),
            sa.Column('title_en', sa.Text(), nullable=True, comment='Meeting title in English'),
            sa.Column('title_fr', sa.Text(), nullable=True, comment='Meeting title in French'),
            sa.Column('meeting_type', sa.String(100), nullable=True, comment='Type of meeting'),
            sa.Column('room', sa.String(200), nullable=True, comment='Room location'),
            sa.Column('witnesses', sa.JSON(), nullable=True, comment='List of witnesses (JSON array)'),
            sa.Column('documents', sa.JSON(), nullable=True, comment='Related documents (JSON array)'),
            sa.Column('source_url', sa.String(500), nullable=True, comment='Source URL from OpenParliament'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id', name='pk_committee_meetings'),
            sa.ForeignKeyConstraint(
                ['committee_id'],
                ['committees.id'],
                name='fk_committee_meetings_committee',
                ondelete='CASCADE'
            ),
            comment='Committee meeting records with witnesses and documents'
        )
        
        # Indexes for committee_meetings
        op.create_index('idx_committee_meetings_committee', 'committee_meetings', ['committee_id'])
        op.create_index('idx_committee_meetings_date', 'committee_meetings', ['meeting_date'])
        op.create_index('idx_committee_meetings_parliament_session', 'committee_meetings', ['parliament', 'session'])
        op.create_index('idx_committee_meetings_committee_date', 'committee_meetings', ['committee_id', 'meeting_date'])
        
        # Unique constraint on committee + meeting_number + parliament + session
        op.create_index(
            'uq_committee_meeting_natural_key',
            'committee_meetings',
            ['committee_id', 'meeting_number', 'parliament', 'session'],
            unique=True
        )


def downgrade() -> None:
    """Remove committee_meetings table."""
    
    # Get connection to check existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop committee_meetings table (if exists)
    if 'committee_meetings' in existing_tables:
        # Drop indexes first
        op.drop_index('uq_committee_meeting_natural_key', table_name='committee_meetings', if_exists=True)
        op.drop_index('idx_committee_meetings_committee_date', table_name='committee_meetings', if_exists=True)
        op.drop_index('idx_committee_meetings_parliament_session', table_name='committee_meetings', if_exists=True)
        op.drop_index('idx_committee_meetings_date', table_name='committee_meetings', if_exists=True)
        op.drop_index('idx_committee_meetings_committee', table_name='committee_meetings', if_exists=True)
        
        # Drop table
        op.drop_table('committee_meetings')
