"""complete schema: votes, debates, committees, embeddings, rankings

Revision ID: 2_complete_schema
Revises: 7bd692ce137c
Create Date: 2025-10-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2_complete_schema'
down_revision: Union[str, Sequence[str], None] = '7bd692ce137c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing tables for complete backend."""
    
    # ============================================================================
    # PARTIES TABLE
    # ============================================================================
    op.create_table(
        'parties',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_fr', sa.String(length=200), nullable=True),
        sa.Column('short_name_en', sa.String(length=50), nullable=True),
        sa.Column('short_name_fr', sa.String(length=50), nullable=True),
        sa.Column('abbreviation', sa.String(length=20), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),  # Hex color
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'name_en', name='uq_party_natural_key')
    )
    op.create_index('idx_party_jurisdiction', 'parties', ['jurisdiction'])
    
    # ============================================================================
    # RIDINGS TABLE
    # ============================================================================
    op.create_table(
        'ridings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_fr', sa.String(length=200), nullable=True),
        sa.Column('province', sa.String(length=2), nullable=True),  # AB, BC, etc.
        sa.Column('riding_code', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'name_en', name='uq_riding_natural_key')
    )
    op.create_index('idx_riding_jurisdiction', 'ridings', ['jurisdiction'])
    op.create_index('idx_riding_province', 'ridings', ['province'])
    
    # ============================================================================
    # VOTES TABLE
    # ============================================================================
    op.create_table(
        'votes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('vote_id', sa.String(length=100), nullable=False),  # External ID
        sa.Column('parliament', sa.Integer(), nullable=False),
        sa.Column('session', sa.Integer(), nullable=False),
        sa.Column('vote_number', sa.Integer(), nullable=False),
        sa.Column('chamber', sa.String(length=50), nullable=False),  # House, Senate
        sa.Column('vote_date', sa.DateTime(), nullable=False),
        sa.Column('vote_description_en', sa.Text(), nullable=True),
        sa.Column('vote_description_fr', sa.Text(), nullable=True),
        sa.Column('bill_id', sa.Integer(), nullable=True),  # FK to bills
        sa.Column('result', sa.String(length=50), nullable=False),  # Passed, Defeated
        sa.Column('yeas', sa.Integer(), nullable=False, default=0),
        sa.Column('nays', sa.Integer(), nullable=False, default=0),
        sa.Column('abstentions', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], name='fk_vote_bill'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'vote_id', name='uq_vote_natural_key')
    )
    op.create_index('idx_vote_jurisdiction', 'votes', ['jurisdiction'])
    op.create_index('idx_vote_bill_id', 'votes', ['bill_id'])
    op.create_index('idx_vote_date', 'votes', ['vote_date'])
    op.create_index('idx_vote_parliament_session', 'votes', ['parliament', 'session'])
    
    # ============================================================================
    # VOTE RECORDS TABLE (individual MP votes)
    # ============================================================================
    op.create_table(
        'vote_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vote_id', sa.Integer(), nullable=False),  # FK to votes
        sa.Column('politician_id', sa.Integer(), nullable=False),  # FK to politicians
        sa.Column('vote_position', sa.String(length=20), nullable=False),  # Yea, Nay, Abstain
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['vote_id'], ['votes.id'], name='fk_voterecord_vote'),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name='fk_voterecord_politician'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vote_id', 'politician_id', name='uq_vote_record_natural_key')
    )
    op.create_index('idx_voterecord_vote_id', 'vote_records', ['vote_id'])
    op.create_index('idx_voterecord_politician_id', 'vote_records', ['politician_id'])
    
    # ============================================================================
    # COMMITTEES TABLE
    # ============================================================================
    op.create_table(
        'committees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('committee_code', sa.String(length=50), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_fr', sa.String(length=200), nullable=True),
        sa.Column('chamber', sa.String(length=50), nullable=False),  # House, Senate, Joint
        sa.Column('committee_type', sa.String(length=50), nullable=True),  # Standing, Special
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'committee_code', name='uq_committee_natural_key')
    )
    op.create_index('idx_committee_jurisdiction', 'committees', ['jurisdiction'])
    op.create_index('idx_committee_code', 'committees', ['committee_code'])
    
    # ============================================================================
    # DEBATES TABLE (Hansard sessions)
    # ============================================================================
    op.create_table(
        'debates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('hansard_id', sa.String(length=100), nullable=False),  # External ID
        sa.Column('parliament', sa.Integer(), nullable=False),
        sa.Column('session', sa.Integer(), nullable=False),
        sa.Column('sitting_date', sa.DateTime(), nullable=False),
        sa.Column('chamber', sa.String(length=50), nullable=False),
        sa.Column('debate_type', sa.String(length=100), nullable=True),  # Question Period, etc.
        sa.Column('document_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'hansard_id', name='uq_debate_natural_key')
    )
    op.create_index('idx_debate_jurisdiction', 'debates', ['jurisdiction'])
    op.create_index('idx_debate_sitting_date', 'debates', ['sitting_date'])
    op.create_index('idx_debate_parliament_session', 'debates', ['parliament', 'session'])
    
    # ============================================================================
    # SPEECHES TABLE
    # ============================================================================
    op.create_table(
        'speeches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('debate_id', sa.Integer(), nullable=False),  # FK to debates
        sa.Column('politician_id', sa.Integer(), nullable=True),  # FK to politicians (nullable for Speaker)
        sa.Column('speaker_name', sa.String(length=200), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),  # Order in debate
        sa.Column('language', sa.String(length=2), nullable=True),  # en, fr
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('timestamp_start', sa.Time(), nullable=True),
        sa.Column('timestamp_end', sa.Time(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['debate_id'], ['debates.id'], name='fk_speech_debate'),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name='fk_speech_politician'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('debate_id', 'sequence', name='uq_speech_natural_key')
    )
    op.create_index('idx_speech_debate_id', 'speeches', ['debate_id'])
    op.create_index('idx_speech_politician_id', 'speeches', ['politician_id'])
    
    # ============================================================================
    # DOCUMENTS TABLE (for vector embeddings)
    # ============================================================================
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),  # bill, speech, etc.
        sa.Column('entity_id', sa.Integer(), nullable=False),  # Reference to entity
        sa.Column('content_type', sa.String(length=50), nullable=False),  # full_text, summary
        sa.Column('language', sa.String(length=2), nullable=False),  # en, fr
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'content_type', 'language', name='uq_document_natural_key')
    )
    op.create_index('idx_document_entity', 'documents', ['entity_type', 'entity_id'])
    op.create_index('idx_document_jurisdiction', 'documents', ['jurisdiction'])
    
    # ============================================================================
    # EMBEDDINGS TABLE (vector search)
    # ============================================================================
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),  # FK to documents
        sa.Column('chunk_id', sa.Integer(), nullable=False),  # Chunk sequence
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('vector', sa.Text(), nullable=False),  # JSON array of floats (1536 dims for ada-002)
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=False),
        sa.Column('end_char', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_embedding_document'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_id', name='uq_embedding_natural_key')
    )
    op.create_index('idx_embedding_document_id', 'embeddings', ['document_id'])
    # TODO: Add pgvector extension and HNSW index for fast vector search
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    # op.execute('CREATE INDEX idx_embedding_vector_hnsw ON embeddings USING hnsw (vector vector_cosine_ops)')
    
    # ============================================================================
    # RANKINGS TABLE
    # ============================================================================
    op.create_table(
        'rankings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),  # bill, politician
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('score_breakdown', sa.JSON(), nullable=True),  # Component scores
        sa.Column('computed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_ranking_natural_key')
    )
    op.create_index('idx_ranking_entity', 'rankings', ['entity_type', 'entity_id'])
    op.create_index('idx_ranking_score', 'rankings', ['entity_type', 'score'])
    op.create_index('idx_ranking_computed_at', 'rankings', ['computed_at'])


def downgrade() -> None:
    """Remove added tables."""
    op.drop_table('rankings')
    op.drop_table('embeddings')
    op.drop_table('documents')
    op.drop_table('speeches')
    op.drop_table('debates')
    op.drop_table('committees')
    op.drop_table('vote_records')
    op.drop_table('votes')
    op.drop_table('ridings')
    op.drop_table('parties')
