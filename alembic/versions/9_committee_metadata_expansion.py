"""Expand committee metadata fields and normalize jurisdiction."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9_committee_metadata_expansion"
down_revision: Union[str, None] = "8_committee_slug_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add committee metadata columns, backfill data, and enforce constraints."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("committees")}

    columns_to_add = []
    if "natural_id" not in existing_columns:
        columns_to_add.append(sa.Column("natural_id", sa.String(length=255), nullable=True))
    if "parliament" not in existing_columns:
        columns_to_add.append(sa.Column("parliament", sa.Integer(), nullable=True))
    if "session" not in existing_columns:
        columns_to_add.append(sa.Column("session", sa.Integer(), nullable=True))
    if "acronym_en" not in existing_columns:
        columns_to_add.append(sa.Column("acronym_en", sa.String(length=50), nullable=True))
    if "acronym_fr" not in existing_columns:
        columns_to_add.append(sa.Column("acronym_fr", sa.String(length=50), nullable=True))
    if "short_name_en" not in existing_columns:
        columns_to_add.append(sa.Column("short_name_en", sa.String(length=200), nullable=True))
    if "short_name_fr" not in existing_columns:
        columns_to_add.append(sa.Column("short_name_fr", sa.String(length=200), nullable=True))
    if "parent_committee" not in existing_columns:
        columns_to_add.append(sa.Column("parent_committee", sa.String(length=100), nullable=True))
    if "source_url" not in existing_columns:
        columns_to_add.append(sa.Column("source_url", sa.String(length=500), nullable=True))

    if columns_to_add:
        with op.batch_alter_table("committees") as batch_op:
            for column in columns_to_add:
                batch_op.add_column(column)

        # refresh metadata to include newly added columns
        existing_columns.update(column.name for column in columns_to_add)

    # Standardize jurisdiction strings before generating natural ids
    op.execute(
        """
        UPDATE committees
        SET jurisdiction = 'ca-federal'
        WHERE jurisdiction IS NOT NULL
          AND LOWER(jurisdiction) IN ('ca', 'canada', 'ca-canada', 'ca_federal', 'cafederal', 'ca-federal')
        """
    )

    # Infer parliament/session from meetings when available
    op.execute(
        """
        WITH inferred AS (
            SELECT
                committee_id,
                MAX(parliament) AS parliament,
                MAX(session) AS session
            FROM committee_meetings
            GROUP BY committee_id
        )
        UPDATE committees c
        SET
            parliament = COALESCE(c.parliament, inferred.parliament),
            session = COALESCE(c.session, inferred.session)
        FROM inferred
        WHERE c.id = inferred.committee_id
        """
    )

    # Default missing parliament/session values to current legislature (44th, 1st)
    op.execute(
        """
        UPDATE committees
        SET
            parliament = COALESCE(parliament, 44),
            session = COALESCE(session, 1)
        WHERE parliament IS NULL OR session IS NULL
        """
    )

    # Populate acronyms from committee_code if not already set
    op.execute(
        """
        UPDATE committees
        SET acronym_en = UPPER(TRIM(committee_code))
        WHERE committee_code IS NOT NULL
          AND (acronym_en IS NULL OR TRIM(acronym_en) = '')
        """
    )

    op.execute(
        """
        UPDATE committees
        SET acronym_fr = acronym_en
        WHERE acronym_en IS NOT NULL
          AND (acronym_fr IS NULL OR TRIM(acronym_fr) = '')
        """
    )

    # Populate source_url from available slugs/acronyms
    op.execute(
        """
        UPDATE committees
        SET source_url = 'https://api.openparliament.ca/committees/' ||
                         COALESCE(source_slug, LOWER(TRIM(committee_code))) || '/'
        WHERE committee_code IS NOT NULL
          AND (source_url IS NULL OR TRIM(source_url) = '')
        """
    )

    # Build natural identifiers
    op.execute(
        """
        UPDATE committees
        SET natural_id = LOWER(jurisdiction) || '-' ||
                         parliament || '-' ||
                         session || '-committee-' ||
                         UPPER(TRIM(committee_code))
        WHERE committee_code IS NOT NULL
        """
    )

    # Enforce non-null constraints on required fields
    with op.batch_alter_table("committees") as batch_op:
        if "natural_id" in existing_columns:
            batch_op.alter_column("natural_id", existing_type=sa.String(length=255), nullable=False)
        if "parliament" in existing_columns:
            batch_op.alter_column("parliament", existing_type=sa.Integer(), nullable=False)
        if "session" in existing_columns:
            batch_op.alter_column("session", existing_type=sa.Integer(), nullable=False)
        if "acronym_en" in existing_columns:
            batch_op.alter_column("acronym_en", existing_type=sa.String(length=50), nullable=False)

    # Create indexes and constraints if missing
    inspector = sa.inspect(bind)  # refresh with updated metadata
    existing_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("committees")}
    if "uq_committees_natural_id" not in existing_constraints:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.create_unique_constraint("uq_committees_natural_id", ["natural_id"])

    existing_indexes = {index["name"] for index in inspector.get_indexes("committees")}
    if "idx_committees_parliament" not in existing_indexes:
        op.create_index("idx_committees_parliament", "committees", ["parliament"])
    if "idx_committees_session" not in existing_indexes:
        op.create_index("idx_committees_session", "committees", ["session"])


def downgrade() -> None:
    """Drop metadata indexes/constraints and remove expanded columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {index["name"] for index in inspector.get_indexes("committees")}
    if "idx_committees_session" in existing_indexes:
        op.drop_index("idx_committees_session", table_name="committees")
    if "idx_committees_parliament" in existing_indexes:
        op.drop_index("idx_committees_parliament", table_name="committees")

    existing_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("committees")}
    if "uq_committees_natural_id" in existing_constraints:
        with op.batch_alter_table("committees") as batch_op:
            batch_op.drop_constraint("uq_committees_natural_id", type_="unique")

    columns_to_drop = []
    existing_columns = {column["name"] for column in inspector.get_columns("committees")}
    for column_name in [
        "natural_id",
        "parliament",
        "session",
        "acronym_en",
        "acronym_fr",
        "short_name_en",
        "short_name_fr",
        "parent_committee",
        "source_url",
    ]:
        if column_name in existing_columns:
            columns_to_drop.append(column_name)

    if columns_to_drop:
        with op.batch_alter_table("committees") as batch_op:
            for column_name in columns_to_drop:
                batch_op.drop_column(column_name)
