"""Create emails table

Revision ID: 002
Revises: 001
Create Date: 2021-07-15 21:15:44.746933

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venom_emails",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sender", sa.String(256), nullable=False),
        sa.Column("recipients", sa.TEXT, nullable=False),
        sa.Column("recipients_cc", sa.TEXT),
        sa.Column("recipients_bcc", sa.TEXT),
        sa.Column("subject", sa.String(128)),
        sa.Column("payload", sa.LargeBinary),
        sa.Column("payload_type", sa.String(50)),
        sa.Column(
            "status",
            sa.Enum("Scheduled", "Processing", "Delivered", "Not Sent", name="venom_emails_status"),
            server_default="Scheduled"
        ),
        sa.Column("smtp_code", sa.Integer),
        sa.Column("smtp_error", sa.TEXT),
        sa.Column("date", sa.DateTime),
        sa.Column("created_on", sa.DateTime),
        sa.Column("updated_on", sa.DateTime)
    )


def downgrade():
    op.drop_table("venom_emails")
