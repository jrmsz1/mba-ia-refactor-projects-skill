import re

from models.user import User
from models.task import Task
from config.settings import Config, VALID_USER_ROLES, EMAIL_REGEX
from controllers.task_controller import ValidationError, NotFoundError


class AuthenticationError(Exception):
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _validate_email(email):
    if not email:
        raise ValidationError('Email é obrigatório')
    if not re.match(EMAIL_REGEX, email):
        raise ValidationError('Email inválido')


def _validate_password(password):
    if not password:
        raise ValidationError('Senha é obrigatória')
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f'Senha deve ter no mínimo {Config.MIN_PASSWORD_LENGTH} caracteres'
        )


def _validate_role(role):
    if role not in VALID_USER_ROLES:
        raise ValidationError('Role inválido')


class UserController:

    @staticmethod
    def list_users():
        users = User.get_all()
        return [
            {
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'role': u.role,
                'active': u.active,
                'created_at': str(u.created_at),
                'task_count': len(u.tasks),
            }
            for u in users
        ]

    @staticmethod
    def get_user(user_id):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        data = user.to_dict()
        data['tasks'] = [t.to_dict() for t in Task.list_by_user(user_id)]
        return data

    @staticmethod
    def create_user(data):
        if not data:
            raise ValidationError('Dados inválidos')

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')

        if not name:
            raise ValidationError('Nome é obrigatório')
        _validate_email(email)
        _validate_password(password)
        _validate_role(role)

        if User.email_exists(email):
            raise ValidationError('Email já cadastrado', status_code=409)

        user = User.create(name=name, email=email, password=password, role=role)
        return user.to_dict()

    @staticmethod
    def update_user(user_id, data):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            user.name = data['name']

        if 'email' in data:
            _validate_email(data['email'])
            if User.email_exists(data['email'], exclude_id=user_id):
                raise ValidationError('Email já cadastrado', status_code=409)
            user.email = data['email']

        if 'password' in data:
            _validate_password(data['password'])
            user.set_password(data['password'])

        if 'role' in data:
            _validate_role(data['role'])
            user.role = data['role']

        if 'active' in data:
            user.active = data['active']

        user.save()
        return user.to_dict()

    @staticmethod
    def delete_user(user_id):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        user.delete()

    @staticmethod
    def list_user_tasks(user_id):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')

        tasks = Task.list_by_user(user_id)
        result = []
        for task in tasks:
            data = task.to_dict_with_overdue()
            data.pop('user_id', None)
            data.pop('category_id', None)
            data.pop('updated_at', None)
            data.pop('tags', None)
            result.append(data)
        return result

    @staticmethod
    def authenticate(data):
        if not data:
            raise ValidationError('Dados inválidos')

        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            raise ValidationError('Email e senha são obrigatórios')

        user = User.get_by_email(email)
        if not user or not user.check_password(password):
            raise AuthenticationError('Credenciais inválidas')

        if not user.active:
            raise AuthenticationError('Usuário inativo', status_code=403)

        return {
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': f'fake-jwt-token-{user.id}',
        }
