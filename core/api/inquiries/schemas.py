from typing import Optional

from fastapi import Form
from pydantic import BaseModel, validator

from core.schemas import email_validator


class InquirySchema(BaseModel):

    inquiry_type: str
    name: str
    email: str
    subject: str
    message: str
    send_copy_email: Optional[bool] = True

    _normalized_email = validator("email", allow_reuse=True)(email_validator)

    def __init__(
            self,
            inquiry_type: str = Form(...),
            name: str = Form(...),
            email: str = Form(...),
            subject: str = Form(...),
            message: str = Form(...),
            send_copy_email: bool = Form(True),
    ):
        super().__init__(
            inquiry_type=inquiry_type,
            name=name,
            email=email,
            subject=subject,
            message=message,
            send_copy_email=send_copy_email
        )

    class Config:
        orm_mode = True
