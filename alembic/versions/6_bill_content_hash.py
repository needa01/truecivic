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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {column["name"] for column in inspector.get_columns("bills")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("bills")}

    if "content_hash" not in existing_columns:
        op.add_column("bills", sa.Column("content_hash", sa.String(length=64), nullable=True))

    if "ix_bills_content_hash" not in existing_indexes:
        op.create_index("ix_bills_content_hash", "bills", ["content_hash"], unique=False)


def downgrade() -> None:
    """Remove content_hash column and index."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {index["name"] for index in inspector.get_indexes("bills")}
    if "ix_bills_content_hash" in existing_indexes:
        op.drop_index("ix_bills_content_hash", table_name="bills")

    existing_columns = {column["name"] for column in inspector.get_columns("bills")}
    if "content_hash" in existing_columns:
        op.drop_column("bills", "content_hash")
