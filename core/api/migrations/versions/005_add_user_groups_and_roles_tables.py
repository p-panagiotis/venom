"""Add user groups and roles tables

Revision ID: 005
Revises: 004
Create Date: 2021-09-12 23:29:55.295528

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venom_roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )

    op.create_table(
        "venom_users_roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey(column="venom_users.id", name="venom_users_roles_user_id_fkey", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "role_id",
            sa.Integer,
            sa.ForeignKey(column="venom_roles.id", name="venom_users_roles_role_id_fkey", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )

    op.create_table(
        "venom_user_groups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )

    op.create_table(
        "venom_user_groups_roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_group_id",
            sa.Integer,
            sa.ForeignKey(
                column="venom_user_groups.id",
                name="venom_user_groups_roles_user_group_id_fkey",
                ondelete="CASCADE"
            ),
            nullable=False
        ),
        sa.Column(
            "role_id",
            sa.Integer,
            sa.ForeignKey(column="venom_roles.id", name="venom_user_groups_roles_role_id_fkey", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )

    op.create_table(
        "venom_user_groups_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_group_id",
            sa.Integer,
            sa.ForeignKey(
                column="venom_user_groups.id",
                name="venom_user_groups_users_user_group_id_fkey",
                ondelete="CASCADE"
            ),
            nullable=False
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey(column="venom_users.id", name="venom_user_groups_users_user_id_fkey", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )

    # add unique indexes
    op.create_index(
        index_name="i_venom_users_roles_user_id_role_id",
        table_name="venom_users_roles",
        columns=["user_id", "role_id"],
        unique=True
    )
    op.create_index(
        index_name="i_venom_user_groups_roles_user_group_id_role_id",
        table_name="venom_user_groups_roles",
        columns=["user_group_id", "role_id"],
        unique=True
    )
    op.create_index(
        index_name="i_venom_user_groups_users_user_group_id_user_id",
        table_name="venom_user_groups_users",
        columns=["user_group_id", "user_id"],
        unique=True
    )


def downgrade():
    op.drop_table("venom_user_groups_users")
    op.drop_table("venom_user_groups_roles")
    op.drop_table("venom_users_roles")
    op.drop_table("venom_user_groups")
    op.drop_table("venom_roles")
