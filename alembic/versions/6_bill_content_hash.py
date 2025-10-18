"""Add content hash column to bills table for deduplication."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6_bill_content_hash"
down_revision: Union[str, None] = "5_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Introduce content_hash column and supporting index."""
    with op.batch_alter_table("bills") as batch_op:
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_bills_content_hash", ["content_hash"], unique=False)


def downgrade() -> None:
    """Remove content_hash column and index."""
    with op.batch_alter_table("bills") as batch_op:
        batch_op.drop_index("ix_bills_content_hash")
        batch_op.drop_column("content_hash")
