"""Adiciona states persistidos para o callback OAuth."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_oauth_states"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria a tabela de states OAuth."""
    op.create_table(
        "oauth_states",
        sa.Column("state_token", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("state_token"),
    )


def downgrade() -> None:
    """Remove a tabela de states OAuth."""
    op.drop_table("oauth_states")
