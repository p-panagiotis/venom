
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import Session

from core.models import Model


class Inquiry(Model):
    __tablename__ = "venom_inquiries"

    inquiry_type = Column(String(128))
    name = Column(String(100))
    email = Column(String(256))
    subject = Column(String(128))
    message = Column(Text)
    send_copy_email = Column(Boolean, server_default="1")

    def __init__(self, **kwargs):
        super(Inquiry, self).__init__(**kwargs)

    @classmethod
    async def create(
            cls,
            db: Session,
            inquiry_type: str = None,
            name: str = None,
            email: str = None,
            subject: str = None,
            message: str = None,
            send_copy_email: bool = True,
    ):
        inquiry = cls(
            inquiry_type=inquiry_type,
            name=name,
            email=email,
            subject=subject,
            message=message,
            send_copy_email=send_copy_email
        )

        db.add(inquiry)
        db.flush()
        return inquiry
