from typing import Optional, List

from fastapi import Form
from pydantic import BaseModel, validator

from core.schemas import email_validator


class UserSchema(BaseModel):

    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: str
    email: str

    class Config:
        orm_mode = True


class UserCreateSchema(BaseModel):

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: str
    email: str
    password: str

    _normalized_email = validator("email", allow_reuse=True)(email_validator)

    def __init__(
            self,
            first_name: str = Form(None),
            last_name: str = Form(None),
            username: str = Form(...),
            email: str = Form(...),
            password: str = Form(...)
    ):
        super().__init__(first_name=first_name, last_name=last_name, username=username, email=email, password=password)

    class Config:
        orm_mode = True


class UserResetPasswordSchema(BaseModel):

    email: str

    _normalized_email = validator("email", allow_reuse=True)(email_validator)

    def __init__(self, email: str = Form(...)):
        super().__init__(email=email)


class UserUpdateSchema(BaseModel):

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str

    _normalized_email = validator("email", allow_reuse=True)(email_validator)

    def __init__(self, first_name: str = Form(None), last_name: str = Form(None), email: str = Form(...)):
        super().__init__(first_name=first_name, last_name=last_name, email=email)


class RoleSchema(BaseModel):

    id: int
    name: str
    description: Optional[str] = None
    users_count: Optional[int] = 0

    class Config:
        orm_mode = True


class RolesSchema(BaseModel):
    __root__: List[RoleSchema]


class UserGroupSchema(BaseModel):

    id: int
    name: str
    description: Optional[str] = None
    users_count: Optional[int] = 0
    roles_count: Optional[int] = 0

    class Config:
        orm_mode = True


class UserGroupsSchema(BaseModel):
    __root__: List[UserGroupSchema]

