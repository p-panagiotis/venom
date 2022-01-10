from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import jwt, JWTError

from core.venom import cfg

SECRET_KEY = cfg["core.api.oauth2.secret_key"]
ALGORITHM = cfg["core.api.oauth2.algorithm"]


def create_access_token(data: dict, expires_in_minutes: int):
    to_encode = data.copy()

    expires_delta = timedelta(minutes=expires_in_minutes)
    exp = datetime.utcnow() + expires_delta

    to_encode.update(exp=exp)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (Exception, JWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized request",
            headers={"WWW-Authenticate": "Bearer"},
        )
