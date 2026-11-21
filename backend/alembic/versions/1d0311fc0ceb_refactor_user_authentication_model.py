"""refactor user authentication model

Revision ID: 1d0311fc0ceb
Revises: d791b7289f1c
Create Date: 2026-07-17 23:19:17.861137
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1d0311fc0ceb"
down_revision: Union[str, Sequence[str], None] = "d791b7289f1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    auth_provider_enum = sa.Enum(
        "local",
        "google",
        name="auth_provider",
    )
    auth_provider_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column("username", sa.String(30), nullable=False),
    )

    op.add_column(
        "users",
        sa.Column("full_name", sa.String(100), nullable=False),
    )

    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            auth_provider_enum,
            nullable=False,
            server_default="local",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "provider_user_id",
            sa.String(255),
            nullable=True,
        ),
    )

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(20),
        nullable=False,
    )

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=True,
    )

    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )

    op.create_unique_constraint(
        "uq_users_provider_user_id",
        "users",
        ["provider_user_id"],
    )

    op.alter_column(
        "users",
        "auth_provider",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "uq_users_provider_user_id",
        "users",
        type_="unique",
    )

    op.drop_index(
        "ix_users_username",
        table_name="users",
    )

    op.drop_column("users", "provider_user_id")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "full_name")
    op.drop_column("users", "username")

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(20),
        nullable=True,
    )

    sa.Enum(
        "local",
        "google",
        name="auth_provider",
    ).drop(op.get_bind(), checkfirst=True)