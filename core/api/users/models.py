import logging

from passlib.context import CryptContext
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship, Session

from core.api.users.exceptions import UserUsernameAlreadyInUseException, UserEmailAlreadyInUseException, \
    UserNotFoundException, UserOldPasswordCannotBeVerifiedException, UserPasswordsCannotBeConfirmedException, \
    UserGroupAlreadyAssignedWithRoleException, UserAlreadyAssignedWithRoleException, UserGroupAlreadyInUseException, \
    UserGroupNotFoundException
from core.models import Model

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)


class User(Model):
    __tablename__ = "venom_users"

    first_name = Column(String(50))
    last_name = Column(String(50))
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(256), unique=True)
    password = Column(String(256))
    _roles = relationship("UserRole", back_populates="user")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

        self.set_password(password=self.password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)

    def set_password(self, password):
        self.password = self.hash_password(password=password)
        return self

    @property
    def roles(self):
        return [user_role.role.name for user_role in self._roles]

    async def update(
            self,
            db: Session,
            first_name: str = None,
            last_name: str = None,
            email: str = None
    ):
        if self.first_name != first_name:
            self.first_name = first_name

        if self.last_name != last_name:
            self.last_name = last_name

        if self.email != email:
            # verify email if already in use
            if await self.get_by_email(email=email, db=db):
                raise UserEmailAlreadyInUseException(email=email)

            self.email = email

        return self

    async def update_password(self, new_pwd: str, confirm_pwd: str, old_pwd: str = None):
        if old_pwd and not self.verify_password(old_pwd):
            raise UserOldPasswordCannotBeVerifiedException()

        if new_pwd != confirm_pwd:
            raise UserPasswordsCannotBeConfirmedException()

        self.set_password(password=new_pwd)
        return self

    async def has_role(self, role_name: str, db: Session):
        role = await Role.get_by_name(name=role_name, db=db)
        if not role:
            return False

        user_role = db.query(UserRole).filter(UserRole.user_id == self.id).filter(UserRole.role_id == role.id).first()
        return user_role is not None

    @classmethod
    async def get_by_username(cls, username: str, db: Session):
        user = db.query(cls).filter(cls.username == username).first()
        return user

    @classmethod
    async def get_by_email(cls, email: str, db: Session):
        user = db.query(cls).filter(cls.email == email).first()
        return user

    @classmethod
    async def get_by_id(cls, id: int, db: Session):
        user = db.query(User).filter(User.id == id).first()

        if not user:
            raise UserNotFoundException(user_id=id)
        return user

    @classmethod
    async def create(
            cls,
            username: str,
            email: str,
            password: str,
            db: Session,
            first_name: str = None,
            last_name: str = None
    ):
        # verify username if already in use
        if await cls.get_by_username(username=username, db=db):
            raise UserUsernameAlreadyInUseException(username=username)

        # verify email if already in use
        if await cls.get_by_email(email=email, db=db):
            raise UserEmailAlreadyInUseException(email=email)

        # add new user
        user = cls(first_name=first_name, last_name=last_name, username=username, email=email, password=password)

        db.add(user)
        db.flush()
        return user

    @classmethod
    async def delete(cls, id: int, db: Session):
        try:
            user = await cls.get_by_id(id=id, db=db)

            db.delete(user)
            db.flush()
            return user
        except UserNotFoundException as e:
            logger.warning(str(e))

    @staticmethod
    def hash_password(password):
        return pwd_context.hash(password)


class UserBlacklistedToken(Model):
    __tablename__ = "venom_users_blacklisted_tokens"

    token = Column(String(128), nullable=False)

    user_id = Column("user_id", Integer, ForeignKey("venom_users.id"), nullable=False)
    user = relationship(User, primaryjoin=User.id == user_id)

    def __init__(self, **kwargs):
        super(UserBlacklistedToken, self).__init__(**kwargs)


class Role(Model):
    __tablename__ = "venom_roles"

    name = Column(String(50), nullable=False)
    description = Column(Text)
    _users = relationship("UserRole", back_populates="role", cascade="all, delete")

    @property
    def users(self):
        return [user_role.user for user_role in self._users]

    @classmethod
    async def create(cls, db: Session, name: str, description: str = None):
        role = await cls.get_by_name(name=name, db=db)
        if not role:
            role = cls(name=name, description=description)
            db.add(role)
            db.flush()

        return role

    @classmethod
    async def get_by_name(cls, db: Session, name):
        role = db.query(cls).filter(cls.name == name).first()
        return role

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)


class UserRole(Model):
    __tablename__ = "venom_users_roles"

    user_id = Column("user_id", Integer, ForeignKey("venom_users.id"), nullable=False)
    user = relationship(User, primaryjoin=User.id == user_id)

    role_id = Column("role_id", Integer, ForeignKey("venom_roles.id"), nullable=False)
    role = relationship(Role, primaryjoin=Role.id == role_id)

    @classmethod
    async def create(cls, user: User, role: Role, db: Session):
        if await user.has_role(role_name=role.name, db=db):
            raise UserAlreadyAssignedWithRoleException(username=user.username, role_name=role.name)

        user_role = cls(user=user, role=role)
        db.add(user_role)
        db.flush()
        return user_role

    def __init__(self, **kwargs):
        super(UserRole, self).__init__(**kwargs)


class UserGroup(Model):
    __tablename__ = "venom_user_groups"

    name = Column(String(50), nullable=False)
    description = Column(Text)
    _users = relationship("UserGroupUser", back_populates="user_group", cascade="all, delete")
    _roles = relationship("UserGroupRole", back_populates="user_group", cascade="all, delete")

    @property
    def users(self):
        return [entity.user for entity in self._users]

    @property
    def roles(self):
        return [entity.role for entity in self._roles]

    async def has_role(self, role_name: str, db: Session):
        role = await Role.get_by_name(name=role_name, db=db)
        if not role:
            return False

        user_group_role = db.query(UserGroupRole)\
            .filter(UserGroupRole.user_group_id == self.id)\
            .filter(UserGroupRole.role_id == role.id)\
            .first()
        return user_group_role is not None

    @classmethod
    async def create(cls, db: Session, name: str, description: str = None):
        user_group = await cls.get_by_name(name=name, db=db)

        if user_group:
            raise UserGroupAlreadyInUseException(name=name)

        user_group = cls(name=name, description=description)
        db.add(user_group)
        db.flush()
        return user_group

    @classmethod
    async def get_by_name(cls, db: Session, name):
        user_group = db.query(cls).filter(cls.name == name).first()
        return user_group

    @classmethod
    async def get_by_id(cls, db: Session, id):
        user_group = db.query(cls).filter(cls.id == id).first()

        if not user_group:
            raise UserGroupNotFoundException(user_group_id=id)

        return user_group

    def __init__(self, **kwargs):
        super(UserGroup, self).__init__(**kwargs)


class UserGroupRole(Model):
    __tablename__ = "venom_user_groups_roles"

    user_group_id = Column("user_group_id", Integer, ForeignKey("venom_user_groups.id"), nullable=False)
    user_group = relationship(UserGroup, primaryjoin=UserGroup.id == user_group_id)

    role_id = Column("role_id", Integer, ForeignKey("venom_roles.id"), nullable=False)
    role = relationship(Role, primaryjoin=Role.id == role_id)

    @classmethod
    async def create(cls, user_group: UserGroup, role: Role, db: Session):
        if await user_group.has_role(role_name=role.name, db=db):
            raise UserGroupAlreadyAssignedWithRoleException(user_group_name=user_group.name, role_name=role.name)

        user_group_role = cls(user_group=user_group, role=role)
        db.add(user_group_role)
        db.flush()
        return user_group_role

    def __init__(self, **kwargs):
        super(UserGroupRole, self).__init__(**kwargs)


class UserGroupUser(Model):
    __tablename__ = "venom_user_groups_users"

    user_group_id = Column("user_group_id", Integer, ForeignKey("venom_user_groups.id"), nullable=False)
    user_group = relationship(UserGroup, primaryjoin=UserGroup.id == user_group_id)

    user_id = Column("user_id", Integer, ForeignKey("venom_users.id"), nullable=False)
    user = relationship(User, primaryjoin=User.id == user_id)

    def __init__(self, **kwargs):
        super(UserGroupUser, self).__init__(**kwargs)
