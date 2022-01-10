import logging
import ssl
from datetime import datetime

from fastapi import status

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPResponseException, SMTPHeloError, SMTPRecipientsRefused, \
    SMTPSenderRefused

from core.api.emails.models import Email
from core.context_managers import session_scope
from core.venom import cfg, templates

logger = logging.getLogger(__name__)


async def send_email(
        template,
        recipients,
        subject=None,
        recipients_cc=None,
        recipients_bcc=None,
        payload_data=None,
        payload_type="html"
):
    recipients_cc = recipients_cc if recipients_cc else list()
    recipients_bcc = recipients_bcc if recipients_bcc else list()
    payload_data = payload_data if payload_data else dict()
    payload_data.update(product_name=cfg["core.app_name"])

    # configuration parameters
    from_mask = cfg["core.api.emails.from_mask"]
    smtp_host = cfg["core.api.emails.smtp_host"]
    smtp_port = cfg["core.api.emails.smtp_port"]
    from_addr = cfg["core.api.emails.user"]
    password = cfg["core.api.emails.password"]

    recipients_addrs = recipients + recipients_cc + recipients_bcc
    to_addrs = "; ".join(recipients)
    cc_addrs = "; ".join(recipients_cc)
    bcc_addrs = "; ".join(recipients_bcc)

    # construct multipart payload
    multipart = MIMEMultipart()
    multipart["Subject"] = subject
    multipart["From"] = from_mask
    multipart["To"] = to_addrs
    multipart["Cc"] = cc_addrs
    multipart["Bcc"] = bcc_addrs

    # render templates
    template = templates.get_template(name=template)
    rendered_template = template.render(**payload_data)
    multipart.attach(MIMEText(rendered_template, payload_type))

    # print email on mock smtp host
    if smtp_host is None or smtp_host.strip() == "mock":
        print(multipart.as_string())
        return

    try:
        # create email entity
        with session_scope() as session:
            email = Email(
                sender=from_addr,
                recipients=to_addrs,
                recipients_cc=cc_addrs,
                recipients_bcc=bcc_addrs,
                subject=subject,
                payload=multipart.as_bytes(),
                payload_type=payload_type,
                status=Email.PROCESSING
            )
            session.add(email)

        # create ssl context and send email
        context = ssl.create_default_context()
        with SMTP_SSL(host=smtp_host, port=smtp_port, context=context) as server:
            server.ehlo()
            server.login(user=from_addr, password=password)
            server.sendmail(from_addr=from_addr, to_addrs=recipients_addrs, msg=multipart.as_string())

        email.status = Email.DELIVERED
    except (SMTPAuthenticationError, SMTPResponseException, SMTPHeloError, SMTPRecipientsRefused, SMTPSenderRefused) as e:
        logger.exception(e)
        email.smtp_code = e.smtp_code
        email.smtp_error = str(e.smtp_error)
        email.status = Email.NOT_SENT
    except Exception as e:
        email.smtp_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        email.smtp_error = str(e)
        email.status = Email.NOT_SENT
    finally:
        email.date = datetime.utcnow()

    # update email entity
    with session_scope() as session:
        session.add(email)

    return email
