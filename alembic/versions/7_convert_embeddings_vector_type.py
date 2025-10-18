"""Convert embeddings.vector column to pgvector type."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "7_convert_embeddings_vector_type"
down_revision: Union[str, None] = "6_bill_content_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the text column and recreate it as a pgvector."""
    with op.batch_alter_table("embeddings") as batch_op:
        batch_op.drop_column("vector")

    op.add_column("embeddings", sa.Column("vector", Vector(1536), nullable=False))


def downgrade() -> None:
    """Revert vector column back to text."""
    with op.batch_alter_table("embeddings") as batch_op:
        batch_op.drop_column("vector")

    op.add_column("embeddings", sa.Column("vector", sa.Text(), nullable=False))
