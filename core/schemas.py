import logging

from email_validator import validate_email, EmailNotValidError, caching_resolver

logger = logging.getLogger(__name__)
dns_resolver = caching_resolver(timeout=0)


def email_validator(value: str):
    try:
        # validate email
        valid = validate_email(value, dns_resolver=dns_resolver)

        # normalized form
        email = valid.email
        return email
    except EmailNotValidError as e:
        raise e
