"""Add roles and optional user role relation.

Revision ID: 9b3d4f7a1c2e
Revises: 6d62029bb66e
Create Date: 2026-09-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = "9b3d4f7a1c2e"
down_revision = "6d62029bb66e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=False)
    op.add_column("users", sa.Column("role_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_users_role_id_roles", "users", "roles", ["role_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_role_id_roles", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
