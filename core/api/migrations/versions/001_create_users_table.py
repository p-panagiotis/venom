"""Create users table

Revision ID: 001
Revises: 
Create Date: 2021-07-10 23:14:04.180536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venom_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("first_name", sa.String(50)),
        sa.Column("last_name", sa.String(50)),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(256), unique=True),
        sa.Column("password", sa.String(256)),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )


def downgrade():
    op.drop_table("venom_users")
