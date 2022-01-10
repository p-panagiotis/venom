from fastapi import Depends, HTTPException, status
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session

from core.api.authorization.roles import Role
from core.api.oauth2.oauth2lib import OAuth2PasswordBearerCookie
from core.api.oauth2.security import decode_token
from core.api.users.models import User
from core.database import get_db

oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="/core/api/oauth2/token")


async def oauth2(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token=token)
    username: str = payload.get("sub")

    user = db.query(User).outerjoin(User._roles).filter(User.username == username).first()

    if not user or (Role.SUPER_ADMIN not in user.roles and not set(user.roles).issubset(security_scopes.scopes)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized request",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user
