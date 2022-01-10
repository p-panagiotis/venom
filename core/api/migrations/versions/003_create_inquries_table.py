"""Create inquries table

Revision ID: 003
Revises: 002
Create Date: 2021-07-20 19:52:36.716459

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venom_inquiries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("inquiry_type", sa.String(128)),
        sa.Column("name", sa.String(100)),
        sa.Column("email", sa.String(256)),
        sa.Column("subject", sa.String(128)),
        sa.Column("message", sa.Text),
        sa.Column("send_copy_email", sa.Boolean, server_default="1"),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )


def downgrade():
    op.drop_table("venom_inquiries")
