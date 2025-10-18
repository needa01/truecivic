"""Add committee_slug and source_slug columns to committees table."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8_committee_slug_columns"
down_revision: Union[str, None] = "7_convert_embeddings_vector_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new slug columns and backfill existing records."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("committees")}

    columns_to_add = []
    if "committee_slug" not in existing_columns:
        columns_to_add.append(sa.Column("committee_slug", sa.String(length=100), nullable=True))
    if "source_slug" not in existing_columns:
        columns_to_add.append(sa.Column("source_slug", sa.String(length=100), nullable=True))

    if columns_to_add:
        with op.batch_alter_table("committees") as batch_op:
            for column in columns_to_add:
                batch_op.add_column(column)

    # Normalize jurisdiction to canonical value before deduplication
    op.execute(
        "UPDATE committees SET jurisdiction = 'ca-federal' "
        "WHERE jurisdiction IS NOT NULL AND LOWER(jurisdiction) IN ('ca', 'canada', 'ca-canada', 'ca_federal', 'cafederal')"
    )

    # Reassign related rows to canonical committee ids before deduplication
    op.execute(
        """
        WITH duplicate_map AS (
            SELECT
                id,
                jurisdiction,
                LOWER(TRIM(committee_code)) AS normalized_code,
                MIN(id) OVER (PARTITION BY jurisdiction, LOWER(TRIM(committee_code))) AS canonical_id
            FROM committees
            WHERE committee_code IS NOT NULL
        ),
        updates AS (
            SELECT id, canonical_id
            FROM duplicate_map
            WHERE id <> canonical_id
        )
        UPDATE committee_meetings cm
        SET committee_id = u.canonical_id
        FROM updates u
        WHERE cm.committee_id = u.id
        """
    )

    # Remove duplicate committee rows after reassignment
    op.execute(
        """
        DELETE FROM committees c
        USING (
            SELECT id, canonical_id
            FROM (
                SELECT
                    id,
                    MIN(id) OVER (PARTITION BY jurisdiction, LOWER(TRIM(committee_code))) AS canonical_id
                FROM committees
                WHERE committee_code IS NOT NULL
            ) d
            WHERE id <> canonical_id
        ) duplicates
        WHERE c.id = duplicates.id
        """
    )

    # Normalize committee codes after deduplication
    op.execute("UPDATE committees SET committee_code = UPPER(TRIM(committee_code)) WHERE committee_code IS NOT NULL")

    op.execute(
        """
        UPDATE committees
        SET committee_slug = 'ca-' || UPPER(committee_code)
        WHERE committee_slug IS NULL AND committee_code IS NOT NULL
        """
    )

    with op.batch_alter_table("committees") as batch_op:
        batch_op.alter_column("committee_slug", existing_type=sa.String(length=100), nullable=False)

    existing_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("committees")}
    if "uq_committee_slug" not in existing_constraints:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.create_unique_constraint("uq_committee_slug", ["committee_slug"])

    existing_indexes = {index["name"] for index in inspector.get_indexes("committees")}
    if "idx_committee_slug" not in existing_indexes:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.create_index("idx_committee_slug", ["committee_slug"])


def downgrade() -> None:
    """Remove slug columns and associated constraints."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {index["name"] for index in inspector.get_indexes("committees")}
    if "idx_committee_slug" in existing_indexes:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.drop_index("idx_committee_slug")

    existing_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("committees")}
    if "uq_committee_slug" in existing_constraints:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.drop_constraint("uq_committee_slug", type_="unique")

    existing_columns = {column["name"] for column in inspector.get_columns("committees")}
    columns_to_drop = []
    if "source_slug" in existing_columns:
        columns_to_drop.append("source_slug")
    if "committee_slug" in existing_columns:
        columns_to_drop.append("committee_slug")

    if columns_to_drop:
        with op.batch_alter_table("committees") as batch_op:
            for column in columns_to_drop:
                batch_op.drop_column(column)
