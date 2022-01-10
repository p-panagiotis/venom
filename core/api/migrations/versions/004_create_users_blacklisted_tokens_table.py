"""Create users blacklisted tokens table

Revision ID: 004
Revises: 003
Create Date: 2021-08-31 09:44:12.905962

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import ForeignKey

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venom_users_blacklisted_tokens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            ForeignKey(column="venom_users.id", name="venom_users_blacklisted_tokens_user_id_fkey", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("token", sa.String(256), nullable=False),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )


def downgrade():
    op.drop_table("venom_users_blacklisted_tokens")
