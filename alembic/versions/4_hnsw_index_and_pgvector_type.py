"""convert embeddings vector column to pgvector and add HNSW index

Revision ID: 4_hnsw_vector
Revises: 3_personalization
Create Date: 2025-10-21 04:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4_hnsw_vector"
down_revision: Union[str, Sequence[str], None] = "3_personalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert embeddings.vector to pgvector type and add HNSW index."""

    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        ALTER TABLE embeddings
        ALTER COLUMN vector TYPE vector(1536)
        USING CASE
            WHEN vector IS NULL THEN NULL
            ELSE vector::vector(1536)
        END
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
        ON embeddings
        USING hnsw ("vector" vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Revert embeddings.vector to TEXT and drop HNSW index."""

    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_hnsw")
    op.execute(
        """
        ALTER TABLE embeddings
        ALTER COLUMN vector TYPE TEXT
        USING vector::text
        """
    )

