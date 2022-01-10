from core.venom import messages


class UserUsernameAlreadyInUseException(Exception):

    def __init__(self, username):
        self.detail = messages["core.api.users.username_already_in_use"] % username
        super(UserUsernameAlreadyInUseException, self).__init__(self.detail)


class UserEmailAlreadyInUseException(Exception):

    def __init__(self, email):
        self.detail = messages["core.api.users.email_already_in_use"] % email
        super(UserEmailAlreadyInUseException, self).__init__(self.detail)


class UserNotFoundException(Exception):

    def __init__(self, user_id):
        self.detail = messages["core.api.users.user_not_found"] % user_id
        super(UserNotFoundException, self).__init__(self.detail)


class UserOldPasswordCannotBeVerifiedException(Exception):

    def __init__(self):
        self.detail = messages["core.api.users.user_old_password_cannot_be_verified"]
        super(UserOldPasswordCannotBeVerifiedException, self).__init__(self.detail)


class UserPasswordsCannotBeConfirmedException(Exception):

    def __init__(self):
        self.detail = messages["core.api.users.user_passwords_cannot_be_confirmed"]
        super(UserPasswordsCannotBeConfirmedException, self).__init__(self.detail)


class UserGroupNotFoundException(Exception):

    def __init__(self, user_group_id):
        self.detail = messages["core.api.users.user_group_not_found"] % user_group_id
        super(UserGroupNotFoundException, self).__init__(self.detail)


class UserGroupAlreadyAssignedWithRoleException(Exception):

    def __init__(self, user_group_name, role_name):
        self.detail = messages["core.api.users.user_group_already_assigned_with_role"] % (user_group_name, role_name)
        super(UserGroupAlreadyAssignedWithRoleException, self).__init__(self.detail)


class UserGroupAlreadyInUseException(Exception):

    def __init__(self, name):
        self.detail = messages["core.api.users.user_group_already_in_use"] % name
        super(UserGroupAlreadyInUseException, self).__init__(self.detail)


class UserAlreadyAssignedWithRoleException(Exception):

    def __init__(self, username, role_name):
        self.detail = messages["core.api.users.user_already_assigned_with_role"] % (username, role_name)
        super(UserAlreadyAssignedWithRoleException, self).__init__(self.detail)
