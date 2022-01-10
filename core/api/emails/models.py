from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, LargeBinary

from core.models import Model


class Email(Model):
    __tablename__ = "venom_emails"

    SCHEDULED = "Scheduled"
    PROCESSING = "Processing"
    DELIVERED = "Delivered"
    NOT_SENT = "Not Sent"

    sender = Column(String(256), nullable=False)
    recipients = Column(Text, nullable=False)
    recipients_cc = Column(Text)
    recipients_bcc = Column(Text)
    subject = Column(String(128))
    payload = Column(LargeBinary)
    payload_type = Column(String(50))
    status = Column(
        Enum(SCHEDULED, PROCESSING, DELIVERED, NOT_SENT, name="venom_emails_status"), server_default=SCHEDULED
    )
    smtp_code = Column(Integer)
    smtp_error = Column(Text)
    date = Column(DateTime)

    def __init__(self, **kwargs):
        super(Email, self).__init__(**kwargs)
