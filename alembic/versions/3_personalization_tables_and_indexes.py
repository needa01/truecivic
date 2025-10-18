"""add personalization tables and materialized views

Revision ID: 3_personalization
Revises: 2_complete_schema
Create Date: 2025-01-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3_personalization'
down_revision: Union[str, None] = '2_complete_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add personalization tables and materialized views."""
    
    # 1. Create ignored_bill table for user bill preferences
    op.create_table(
        'ignored_bill',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('natural_id', sa.String(length=255), nullable=False, comment='Unique identifier for this ignore record'),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False, comment='Jurisdiction (e.g., ca-federal)'),
        sa.Column('device_id', sa.String(length=255), nullable=False, comment='Anonymous device identifier'),
        sa.Column('bill_id', sa.Integer(), nullable=False, comment='Foreign key to bills.id'),
        sa.Column('ignored_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('natural_id', 'jurisdiction', name='pk_ignored_bill'),
        sa.ForeignKeyConstraint(
            ['bill_id'],
            ['bills.id'],
            name='fk_ignored_bill_bill',
            ondelete='CASCADE'
        ),
        comment='Bills ignored by anonymous users'
    )
    
    # Indexes for ignored_bill
    op.create_index('idx_ignored_bill_device', 'ignored_bill', ['device_id', 'jurisdiction'])
    op.create_index('idx_ignored_bill_bill', 'ignored_bill', ['bill_id'])
    op.create_index('idx_ignored_bill_ignored_at', 'ignored_bill', ['ignored_at'])
    
    
    # 2. Create personalized_feed_token table for feed subscriptions
    op.create_table(
        'personalized_feed_token',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('natural_id', sa.String(length=255), nullable=False, comment='Token UUID'),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False, comment='Jurisdiction (e.g., ca-federal)'),
        sa.Column('device_id', sa.String(length=255), nullable=False, comment='Anonymous device identifier'),
        sa.Column('token', sa.String(length=255), nullable=False, comment='Unique feed token'),
        sa.Column('feed_type', sa.String(length=50), nullable=False, comment='Type: bills, votes, debates, all'),
        sa.Column('filters_json', postgresql.JSONB(), nullable=True, comment='Filter preferences as JSON'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True, comment='Last time feed was accessed'),
        sa.Column('access_count', sa.Integer(), server_default='0', nullable=False, comment='Number of accesses'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('natural_id', 'jurisdiction', name='pk_personalized_feed_token'),
        sa.UniqueConstraint('token', name='uq_personalized_feed_token_token'),
        comment='Personalized feed tokens for anonymous users'
    )
    
    # Indexes for personalized_feed_token
    op.create_index('idx_feed_token_device', 'personalized_feed_token', ['device_id', 'jurisdiction'])
    op.create_index('idx_feed_token_token', 'personalized_feed_token', ['token'], unique=True)
    op.create_index('idx_feed_token_last_accessed', 'personalized_feed_token', ['last_accessed'])
    
    
    # 3. Create materialized view: mv_feed_all (unified feed of all content)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_feed_all AS
        SELECT 
            'bill' AS entity_type,
            b.id AS entity_id,
            b.jurisdiction,
            b.introduced_date AS event_date,
            'introduced' AS event_type,
            b.number AS title,
            b.title_en AS description,
            COALESCE(b.updated_at, b.created_at) AS updated_at,
            b.parliament,
            b.session
        FROM bills b
        WHERE b.introduced_date IS NOT NULL
        
        UNION ALL
        
        SELECT 
            'vote' AS entity_type,
            v.id AS entity_id,
            v.jurisdiction,
            v.vote_date AS event_date,
            'vote' AS event_type,
            'Vote ' || v.vote_number::text AS title,
            v.vote_description_en AS description,
            COALESCE(v.updated_at, v.created_at) AS updated_at,
            v.parliament,
            v.session
        FROM votes v
        WHERE v.vote_date IS NOT NULL
        
        UNION ALL
        
        SELECT 
            'debate' AS entity_type,
            d.id AS entity_id,
            d.jurisdiction,
            d.sitting_date AS event_date,
            'debate' AS event_type,
            COALESCE(d.debate_type, 'Debate') AS title,
            d.hansard_id AS description,
            COALESCE(d.updated_at, d.created_at) AS updated_at,
            d.parliament,
            d.session
        FROM debates d
        WHERE d.sitting_date IS NOT NULL
        
        ORDER BY event_date DESC NULLS LAST, updated_at DESC;
    """)
    
    # Index on mv_feed_all
    op.create_index('idx_mv_feed_all_event_date', 'mv_feed_all', ['event_date', 'jurisdiction'])
    op.create_index('idx_mv_feed_all_type', 'mv_feed_all', ['entity_type', 'jurisdiction'])
    op.create_index('idx_mv_feed_all_parliament', 'mv_feed_all', ['parliament', 'session'])
    
    
    # 4. Create materialized view: mv_feed_bills_latest (latest bill updates)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_feed_bills_latest AS
        SELECT 
            b.id,
            b.jurisdiction,
            b.number,
            b.title_en,
            b.title_fr,
            b.introduced_date,
            b.parliament,
            b.session,
            b.law_status,
            b.legisinfo_status,
            b.updated_at
        FROM bills b
        WHERE b.introduced_date IS NOT NULL
        ORDER BY b.introduced_date DESC, b.updated_at DESC
        LIMIT 500;
    """)
    
    # Index on mv_feed_bills_latest
    op.create_index('idx_mv_feed_bills_latest_date', 'mv_feed_bills_latest', ['introduced_date'])
    op.create_index('idx_mv_feed_bills_latest_parliament', 'mv_feed_bills_latest', ['parliament', 'session'])
    
    
    # 5. Create materialized view: mv_feed_bills_by_tag (bills grouped by tag)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_feed_bills_by_tag AS
        SELECT 
            tag,
            b.id,
            b.jurisdiction,
            b.number,
            b.title_en,
            b.introduced_date,
            b.parliament,
            b.session,
            b.law_status,
            b.updated_at
        FROM bills b,
        LATERAL json_array_elements_text(b.subject_tags) AS tag
        WHERE b.subject_tags IS NOT NULL 
          AND json_array_length(b.subject_tags) > 0
        ORDER BY tag, b.introduced_date DESC;
    """)
    
    # Index on mv_feed_bills_by_tag
    op.create_index('idx_mv_feed_bills_by_tag_tag', 'mv_feed_bills_by_tag', ['tag', 'jurisdiction'])
    op.create_index('idx_mv_feed_bills_by_tag_date', 'mv_feed_bills_by_tag', ['introduced_date'])
    
    
    # 6. Add HNSW index for pgvector fast vector search on embeddings
    # Note: The embeddings.vector column is currently TEXT type (storing JSON)
    # TODO: Change to proper vector type in future migration, then add HNSW index
    # For now, skip this index creation
    # op.execute("""
    #     CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw 
    #     ON embeddings 
    #     USING hnsw (vector::vector(1536) vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 64);
    # """)
    
    
    # 7. Add GIN indexes for full-text search
    # Add tsvector column for bills if not exists
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'bills' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE bills ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
    """)
    
    # Update search_vector with content
    op.execute("""
        UPDATE bills SET search_vector = 
            setweight(to_tsvector('english', COALESCE(title_en, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(legisinfo_summary_en, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(number, '')), 'C');
    """)
    
    # Create GIN index on search_vector
    op.create_index('idx_bills_search_vector', 'bills', ['search_vector'], postgresql_using='gin')
    
    # Add trigger to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION bills_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title_en, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.legisinfo_summary_en, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.number, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS bills_search_vector_update ON bills;
        
        CREATE TRIGGER bills_search_vector_update 
        BEFORE INSERT OR UPDATE ON bills
        FOR EACH ROW EXECUTE FUNCTION bills_search_vector_trigger();
    """)
    
    # GIN index for debates full-text search
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'debates' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE debates ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
    """)
    
    op.execute("""
        UPDATE debates SET search_vector = 
            setweight(to_tsvector('english', COALESCE(debate_type, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(hansard_id, '')), 'B');
    """)
    
    op.create_index('idx_debates_search_vector', 'debates', ['search_vector'], postgresql_using='gin')
    
    # GIN index for speeches full-text search
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'speeches' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE speeches ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
    """)
    
    op.execute("""
        UPDATE speeches SET search_vector = 
            setweight(to_tsvector('english', COALESCE(text_content, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(speaker_name, '')), 'B');
    """)
    
    op.create_index('idx_speeches_search_vector', 'speeches', ['search_vector'], postgresql_using='gin')


def downgrade() -> None:
    """Remove personalization tables and materialized views."""
    
    # Drop indexes
    op.drop_index('idx_speeches_search_vector', table_name='speeches')
    op.drop_index('idx_debates_search_vector', table_name='debates')
    op.drop_index('idx_bills_search_vector', table_name='bills')
    op.drop_index('idx_embeddings_vector_hnsw', table_name='embeddings')
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS bills_search_vector_update ON bills;")
    op.execute("DROP FUNCTION IF EXISTS bills_search_vector_trigger();")
    
    # Drop search_vector columns
    op.execute("ALTER TABLE bills DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE debates DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE speeches DROP COLUMN IF EXISTS search_vector;")
    
    # Drop materialized view indexes
    op.drop_index('idx_mv_feed_bills_by_tag_date', table_name='mv_feed_bills_by_tag')
    op.drop_index('idx_mv_feed_bills_by_tag_tag', table_name='mv_feed_bills_by_tag')
    op.drop_index('idx_mv_feed_bills_latest_parliament', table_name='mv_feed_bills_latest')
    op.drop_index('idx_mv_feed_bills_latest_date', table_name='mv_feed_bills_latest')
    op.drop_index('idx_mv_feed_all_parliament', table_name='mv_feed_all')
    op.drop_index('idx_mv_feed_all_type', table_name='mv_feed_all')
    op.drop_index('idx_mv_feed_all_event_date', table_name='mv_feed_all')
    
    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_feed_bills_by_tag;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_feed_bills_latest;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_feed_all;")
    
    # Drop personalized_feed_token indexes and table
    op.drop_index('idx_feed_token_last_accessed', table_name='personalized_feed_token')
    op.drop_index('idx_feed_token_token', table_name='personalized_feed_token')
    op.drop_index('idx_feed_token_device', table_name='personalized_feed_token')
    op.drop_table('personalized_feed_token')
    
    # Drop ignored_bill indexes and table
    op.drop_index('idx_ignored_bill_ignored_at', table_name='ignored_bill')
    op.drop_index('idx_ignored_bill_bill', table_name='ignored_bill')
    op.drop_index('idx_ignored_bill_device', table_name='ignored_bill')
    op.drop_table('ignored_bill')
