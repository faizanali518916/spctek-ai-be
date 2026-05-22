"""Add reinstatement report status

Revision ID: f2b7c4d9e801
Revises: a01e22766edc
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2b7c4d9e801"
down_revision: Union[str, Sequence[str], None] = "a01e22766edc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reinstatement_logs",
        sa.Column("report_status", sa.String(length=30), server_default="pending", nullable=False),
    )
    op.add_column("reinstatement_logs", sa.Column("report_error", sa.Text(), nullable=True))
    op.add_column("reinstatement_logs", sa.Column("report_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reinstatement_logs", sa.Column("report_emailed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("reinstatement_logs", "report_emailed_at")
    op.drop_column("reinstatement_logs", "report_generated_at")
    op.drop_column("reinstatement_logs", "report_error")
    op.drop_column("reinstatement_logs", "report_status")
