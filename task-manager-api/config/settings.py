import os
from dotenv import load_dotenv

load_dotenv()


def _get_int(name, default):
    raw = os.environ.get(name)
    return int(raw) if raw is not None and raw != '' else default


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = _get_int('PORT', 5000)

    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = _get_int('SMTP_PORT', 587)
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

    MIN_TITLE_LENGTH = _get_int('MIN_TITLE_LENGTH', 3)
    MAX_TITLE_LENGTH = _get_int('MAX_TITLE_LENGTH', 200)
    MIN_PASSWORD_LENGTH = _get_int('MIN_PASSWORD_LENGTH', 4)
    MIN_PRIORITY = _get_int('MIN_PRIORITY', 1)
    MAX_PRIORITY = _get_int('MAX_PRIORITY', 5)
    DEFAULT_PRIORITY = _get_int('DEFAULT_PRIORITY', 3)
    DEFAULT_CATEGORY_COLOR = os.environ.get('DEFAULT_CATEGORY_COLOR', '#000000')
    RECENT_ACTIVITY_DAYS = _get_int('RECENT_ACTIVITY_DAYS', 7)


VALID_TASK_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
TERMINAL_TASK_STATUSES = ('done', 'cancelled')
VALID_USER_ROLES = ('user', 'admin', 'manager')
EMAIL_REGEX = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'
