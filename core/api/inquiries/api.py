from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from core.api.emails.smtp import send_email
from core.api.inquiries.models import Inquiry
from core.api.inquiries.schemas import InquirySchema
from core.database import get_db
from core.venom import cfg

app = APIRouter(prefix="/core/api/inquiries", tags=["Inquiries"])


@app.post("/", response_model=InquirySchema)
async def api_create_inquiry(
        background_tasks: BackgroundTasks,
        schema: InquirySchema = Depends(),
        db: Session = Depends(get_db)
):
    """
         Creates system inquiry
         - **schema**: inquiry schema for inquiry creation
         - **background_tasks**: send inquiry email in a background task
         - **db**: current database session object
    """
    inquiry = await Inquiry.create(
        inquiry_type=schema.inquiry_type,
        name=schema.name,
        email=schema.email,
        subject=schema.subject,
        message=schema.message,
        send_copy_email=schema.send_copy_email,
        db=db
    )

    support_address = cfg["core.api.inquiries.support_address"]
    inquiry_subject = cfg["core.api.inquiries.support_inquiry_subject"]

    to_addrs = [support_address]
    if schema.send_copy_email:
        to_addrs.append(schema.email)

    background_tasks.add_task(
        func=send_email,
        recipients=to_addrs,
        template="inquiry.html",
        subject=inquiry_subject,
        payload_data=dict(
            user=schema.name,
            inquiry_type=schema.inquiry_type,
            inquiry=schema.subject,
            message=schema.message.replace("\n", "<br />")
        )
    )

    return inquiry
