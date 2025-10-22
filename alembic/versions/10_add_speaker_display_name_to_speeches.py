"""Add speaker_display_name column to speeches."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "10_add_speaker_display_name_to_speeches"
down_revision: Union[str, None] = "9_committee_metadata_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new column for full speaker display names."""
    with op.batch_alter_table("speeches") as batch_op:
        batch_op.add_column(sa.Column("speaker_display_name", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE speeches
        SET speaker_display_name = speaker_name
        WHERE speaker_display_name IS NULL
        """
    )

    with op.batch_alter_table("speeches") as batch_op:
        batch_op.alter_column(
            "speaker_display_name",
            existing_type=sa.Text(),
            nullable=False,
        )


def downgrade() -> None:
    """Remove display name column."""
    with op.batch_alter_table("speeches") as batch_op:
        batch_op.drop_column("speaker_display_name")
