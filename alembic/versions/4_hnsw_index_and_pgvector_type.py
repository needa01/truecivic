"""add pgvector extension safeguards and hnsw index for embeddings

Revision ID: 4_hnsw_vector
Revises: 8_committee_slug_columns
Create Date: 2025-10-21 04:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4_hnsw_vector"
down_revision: Union[str, Sequence[str], None] = "8_committee_slug_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure pgvector extension exists and add HNSW index on embeddings.vector."""

    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
        ON embeddings
        USING hnsw (vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Drop the HNSW index (extension left intact as it may be shared)."""

    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_hnsw")
