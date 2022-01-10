import logging
from time import sleep

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Form, Security
from sqlalchemy import asc
from sqlalchemy.orm import Session
from user_agents import parse

from core.api.authorization.roles import Role as R
from core.api.emails.smtp import send_email
from core.api.oauth2.schemes import oauth2
from core.api.oauth2.security import create_access_token, decode_token
from core.api.users.exceptions import UserUsernameAlreadyInUseException, UserEmailAlreadyInUseException, \
    UserNotFoundException, UserOldPasswordCannotBeVerifiedException, UserPasswordsCannotBeConfirmedException, \
    UserGroupAlreadyInUseException, UserGroupNotFoundException
from core.api.users.models import User, UserBlacklistedToken, Role, UserRole, UserGroup
from core.api.users.schemas import UserSchema, UserCreateSchema, UserResetPasswordSchema, UserUpdateSchema, RoleSchema, \
    RolesSchema, UserGroupsSchema, UserGroupSchema
from core.context_managers import session_scope
from core.database import get_db
from core.models import QueryExecutor
from core.venom import cfg, messages

logger = logging.getLogger(__name__)
app = APIRouter(prefix="/core/api/users", tags=["Users"])


@app.post("/", response_model=UserSchema)
async def api_create_user(schema: UserCreateSchema = Depends(), db: Session = Depends(get_db)):
    """
         Creates system user
         - **schema**: user schema for user creation
         - **db**: current database session object
    """
    try:
        user = await User.create(
            username=schema.username,
            email=schema.email,
            password=schema.password,
            first_name=schema.first_name,
            last_name=schema.last_name,
            db=db
        )

        # assign new user to the USER role
        role = await Role.get_by_name(name=R.USER, db=db)
        if role:
            await UserRole.create(user=user, role=role, db=db)

        return user
    except (UserUsernameAlreadyInUseException, UserEmailAlreadyInUseException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@app.post("/resetpassword/token")
async def api_get_reset_password_token(
        request: Request,
        background_tasks: BackgroundTasks,
        schema: UserResetPasswordSchema = Depends(),
        db: Session = Depends(get_db)
):
    """
         Creates reset password token for the given email address
         - **schema**: user schema for user reset password
         - **db**: current database session object
    """
    user = await User.get_by_email(email=schema.email, db=db)
    if not user:
        # trigger a fake wait in case user not found
        sleep(2)
        return dict()

    token_expires_in = cfg["core.api.users.reset_password_token_expire_hours"]
    expires_in_minutes = token_expires_in * 60
    token = create_access_token(data=dict(sub=user.email), expires_in_minutes=expires_in_minutes)

    support_address = cfg["core.api.inquiries.support_address"]
    subject = cfg["core.api.users.reset_password_subject"]

    ua_string = request.headers.get("user-agent")
    user_agent = parse(user_agent_string=ua_string)
    referrer = request.headers.get("referer").split("?")[0]

    background_tasks.add_task(
        func=send_email,
        recipients=[support_address],
        template="reset_password.html",
        subject=subject,
        payload_data=dict(
            user=user.username,
            token_expires_in=token_expires_in,
            referrer=referrer,
            device=user_agent.get_device(),
            operating_system=user_agent.get_os(),
            browser_name=user_agent.get_browser(),
            token=token,
            support_address=support_address
        )
    )
    return dict()


@app.post("/resetpassword/token/verify")
async def api_verify_reset_password_token(token: str = Form(...), db: Session = Depends(get_db)):
    """
         Verifies reset password token
         - **token**: token to be verified
         - **db**: current database session object
    """
    try:
        # check if token is not blacklisted
        blacklisted_token = db.query(UserBlacklistedToken).filter(UserBlacklistedToken.token == token).first()
        if blacklisted_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        payload = decode_token(token=token)

        email = payload.get("sub")
        user = await User.get_by_email(email=email, db=db)
        return dict(user=dict(id=user.id, username=user.username), expired=False)
    except HTTPException:
        return dict(expired=True)


@app.post("/role", response_model=RoleSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_create_user_role(name: str = Form(...), description: str = Form(None), db: Session = Depends(get_db)):
    """
        Creates system user role
        - **name**: the role name
        - **description**: the role description
        - **db**: current database session object
    """
    if await Role.get_by_name(name=name, db=db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=messages["core.api.users.user_group_already_in_use"] % name
        )

    return await Role.create(name=name, description=description, db=db)


@app.get("/roles", response_model=RolesSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_get_users_roles(db: Session = Depends(get_db)):
    """
        Gets users roles
        - **db**: current database session object
    """
    roles = db.query(Role).outerjoin(Role._users).order_by(asc(Role.id)).all()

    for role in roles:
        role.users_count = len(role.users)

    return roles


@app.get("/groups", response_model=UserGroupsSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_get_users_groups(request: Request, db: Session = Depends(get_db)):
    """
        Gets users groups
        - **db**: current database session object
    """
    user_groups = QueryExecutor(request=request, query=db.query(UserGroup)).all()
    return user_groups


@app.post("/groups", response_model=UserGroupSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_create_user_group(name: str = Form(...), description: str = Form(None), db: Session = Depends(get_db)):
    """
        Creates new user group
        - **name**: the user group name
        - **description**: the user group description
        - **db**: current database session object
    """
    try:
        user_group = await UserGroup.create(name=name, description=description, db=db)
        return user_group
    except UserGroupAlreadyInUseException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@app.get("/groups/{group_id}", response_model=UserGroupSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_get_user_group(group_id: int, db: Session = Depends(get_db)):
    """
        Gets user group
        - **group_id**: the user group id
        - **db**: current database session object
    """
    try:
        user_group = await UserGroup.get_by_id(id=group_id, db=db)
        return user_group
    except UserGroupNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)


@app.put("/groups/{group_id}", response_model=UserGroupSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_update_user_group(group_id: int, name: str = Form(...), description: str = Form(None), db: Session = Depends(get_db)):
    """
        Updates user group
        - **group_id**: the user group id
        - **name**: the user group name
        - **description**: the user group description
        - **db**: current database session object
    """
    try:
        user_group = await UserGroup.get_by_id(id=group_id, db=db)

        if user_group.name != name and name:
            user_group.name = name

        if user_group.description != description:
            user_group.description = description

        return user_group
    except UserGroupNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)


@app.delete("/groups/{group_id}", response_model=UserGroupSchema, dependencies=[Security(oauth2, scopes=R.SUPER_ADMIN)])
async def api_delete_user_group(group_id: int, db: Session = Depends(get_db)):
    """
        Deletes user group
        - **group_id**: the user group id
        - **db**: current database session object
    """
    try:
        user_group = await UserGroup.get_by_id(id=group_id, db=db)
        db.delete(user_group)
        db.flush()

        return user_group
    except UserGroupNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)


@app.get("/{user_id}", response_model=UserSchema, dependencies=[Security(oauth2, scopes=[R.USER, R.ADMIN, R.SUPER_ADMIN])])
async def api_get_user(user_id: int, db: Session = Depends(get_db)):
    """
        Gets user entity
        - **user_id**: the user id
        - **db**: current database session object
    """
    try:
        user = await User.get_by_id(id=user_id, db=db)
        return user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)


@app.put("/{user_id}", response_model=UserSchema, dependencies=[Security(oauth2, scopes=[R.USER, R.ADMIN, R.SUPER_ADMIN])])
async def api_update_user(user_id: int, schema: UserUpdateSchema = Depends(), db: Session = Depends(get_db)):
    """
        Updates user entity
        - **user_id**: the user id
        - **schema**: user schema for user update
        - **db**: current database session object
    """
    try:
        user = await User.get_by_id(id=user_id, db=db)
        await user.update(first_name=schema.first_name, last_name=schema.last_name, email=schema.email, db=db)
        return user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except UserEmailAlreadyInUseException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@app.delete("/{user_id}", response_model=UserSchema, dependencies=[Security(oauth2, scopes=[R.SUPER_ADMIN])])
async def api_update_user(user_id: int, db: Session = Depends(get_db)):
    """
        Deletes user entity and all related data
        - **user_id**: the user id
        - **db**: current database session object
    """
    user = await User.delete(id=user_id, db=db)
    return user


@app.put("/{user_id}/changepassword", response_model=UserSchema, dependencies=[Security(oauth2, scopes=[R.USER, R.ADMIN, R.SUPER_ADMIN])])
async def api_change_user_password(
        user_id: int,
        old_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
        db: Session = Depends(get_db)
):
    """
        Changes user password
        - **user_id**: the user id
        - **old_password**: the old password
        - **new_password**: the new password
        - **confirm_password**: the confirmed new password
        - **db**: current database session object
    """
    try:
        user = await User.get_by_id(id=user_id, db=db)
        await user.update_password(old_pwd=old_password, new_pwd=new_password, confirm_pwd=confirm_password)
        return user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except (UserOldPasswordCannotBeVerifiedException, UserPasswordsCannotBeConfirmedException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@app.put("/{user_id}/resetpassword", response_model=UserSchema)
async def api_reset_user_password(
        user_id: int,
        token: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
        db: Session = Depends(get_db)
):
    """
         Resets user password
         - **user_id**: the user id
         - **token**: the reset password token to be blacklisted
         - **new_password**: the new password
         - **confirm_password**: the confirmed new password
         - **db**: current database session object
    """
    try:
        user = await User.get_by_id(id=user_id, db=db)
        await user.update_password(new_pwd=new_password, confirm_pwd=confirm_password)

        # blacklist token
        blacklisted_token = UserBlacklistedToken(user_id=user.id, token=token)
        db.add(blacklisted_token)

        return user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except UserPasswordsCannotBeConfirmedException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)


@app.on_event("startup")
async def startup_event():
    with session_scope() as db:
        logger.info(f"Setting up built-in {R.SUPER_ADMIN} role...")
        await Role.create(name=R.SUPER_ADMIN, description="Super Administrator of application ecosystem", db=db)

        logger.info(f"Setting up built-in {R.ADMIN} role...")
        await Role.create(name=R.ADMIN, description="Admin of application ecosystem", db=db)

        logger.info(f"Setting up built-in {R.USER} role...")
        await Role.create(name=R.USER, description="User of application ecosystem", db=db)

    logger.info("Built-in roles added!")
