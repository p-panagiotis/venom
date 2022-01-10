from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.api.oauth2.security import create_access_token
from core.api.users.models import User
from core.database import get_db
from core.venom import cfg, messages

app = APIRouter(prefix="/core/api/oauth2", tags=["OAuth2"])


@app.post("/token")
async def api_get_access_token(auth: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
        Authenticates user with the given username and password
        - **auth**: OAuth2PasswordRequestForm class for password flow authentication
        - **db**: Current database session object
    """
    user = await User.get_by_username(username=auth.username, db=db)

    if not user or not user.verify_password(password=auth.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages["core.api.oauth2.authentication_failed"],
            headers={"WWW-Authenticate": "Bearer"}
        )

    expires_in = cfg["core.api.oauth2.access_token_expire_minutes"]
    access_token = create_access_token(data=dict(sub=user.username), expires_in_minutes=expires_in)
    cookie_value = f"Bearer {access_token}"

    response = JSONResponse(content=dict(
        access_token=access_token,
        token_type="Bearer",
        id=user.id,
        username=user.username,
        email=user.email,
        roles=user.roles
    ))
    response.set_cookie(key="Authorization", value=cookie_value, max_age=expires_in * 60, expires=expires_in * 60)
    response.status_code = status.HTTP_200_OK
    return response


@app.post("/logout")
def api_logout_user(response: Response):
    """
        Logout user by deleting Authorization cookie
        - **response**: Current response object
    """
    response.delete_cookie("Authorization")
    response.status_code = status.HTTP_200_OK
    response.headers.append("Content-Type", "application/json")
    return response
