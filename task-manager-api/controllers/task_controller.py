from datetime import datetime

from models.task import Task
from models.user import User
from models.category import Category
from config.settings import Config, VALID_TASK_STATUSES, TERMINAL_TASK_STATUSES


class ValidationError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _parse_due_date(raw):
    try:
        return datetime.strptime(raw, '%Y-%m-%d')
    except (TypeError, ValueError):
        raise ValidationError('Formato de data inválido. Use YYYY-MM-DD')


def _normalize_tags(raw):
    if isinstance(raw, list):
        return ','.join(raw)
    return raw


def _validate_title(title):
    if not title:
        raise ValidationError('Título é obrigatório')
    if len(title) < Config.MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > Config.MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')


def _validate_status(status):
    if status not in VALID_TASK_STATUSES:
        raise ValidationError('Status inválido')


def _validate_priority(priority):
    if not isinstance(priority, int) or priority < Config.MIN_PRIORITY or priority > Config.MAX_PRIORITY:
        raise ValidationError(
            f'Prioridade deve ser entre {Config.MIN_PRIORITY} e {Config.MAX_PRIORITY}'
        )


def _check_user_exists(user_id):
    if user_id and not User.get_by_id(user_id):
        raise NotFoundError('Usuário não encontrado')


def _check_category_exists(category_id):
    if category_id and not Category.get_by_id(category_id):
        raise NotFoundError('Categoria não encontrada')


class TaskController:

    @staticmethod
    def list_tasks():
        tasks = Task.get_all_with_relations()
        result = []
        for task in tasks:
            data = task.to_dict_with_overdue()
            data['user_name'] = task.user.name if task.user else None
            data['category_name'] = task.category.name if task.category else None
            result.append(data)
        return result

    @staticmethod
    def get_task(task_id):
        task = Task.get_by_id(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        return task.to_dict_with_overdue()

    @staticmethod
    def create_task(data):
        if not data:
            raise ValidationError('Dados inválidos')

        title = data.get('title')
        _validate_title(title)

        status = data.get('status', 'pending')
        _validate_status(status)

        priority = data.get('priority', Config.DEFAULT_PRIORITY)
        _validate_priority(priority)

        user_id = data.get('user_id')
        category_id = data.get('category_id')
        _check_user_exists(user_id)
        _check_category_exists(category_id)

        fields = {
            'title': title,
            'description': data.get('description', ''),
            'status': status,
            'priority': priority,
            'user_id': user_id,
            'category_id': category_id,
        }

        if data.get('due_date'):
            fields['due_date'] = _parse_due_date(data['due_date'])

        if data.get('tags') is not None:
            fields['tags'] = _normalize_tags(data['tags'])

        task = Task.create(**fields)
        return task.to_dict()

    @staticmethod
    def update_task(task_id, data):
        task = Task.get_by_id(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        if not data:
            raise ValidationError('Dados inválidos')

        if 'title' in data:
            _validate_title(data['title'])
            task.title = data['title']

        if 'description' in data:
            task.description = data['description']

        if 'status' in data:
            _validate_status(data['status'])
            task.status = data['status']

        if 'priority' in data:
            _validate_priority(data['priority'])
            task.priority = data['priority']

        if 'user_id' in data:
            _check_user_exists(data['user_id'])
            task.user_id = data['user_id']

        if 'category_id' in data:
            _check_category_exists(data['category_id'])
            task.category_id = data['category_id']

        if 'due_date' in data:
            task.due_date = _parse_due_date(data['due_date']) if data['due_date'] else None

        if 'tags' in data:
            task.tags = _normalize_tags(data['tags'])

        task.save()
        return task.to_dict()

    @staticmethod
    def delete_task(task_id):
        task = Task.get_by_id(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        task.delete()

    @staticmethod
    def search_tasks(query, status, priority, user_id):
        priority_value = int(priority) if priority else None
        user_value = int(user_id) if user_id else None
        tasks = Task.search(query=query or None, status=status or None,
                            priority=priority_value, user_id=user_value)
        return [t.to_dict() for t in tasks]

    @staticmethod
    def task_stats():
        total = Task.total()
        status_counts = Task.count_by_status()
        overdue_count = len(Task.list_overdue())
        done = status_counts.get('done', 0)
        return {
            'total': total,
            'pending': status_counts.get('pending', 0),
            'in_progress': status_counts.get('in_progress', 0),
            'done': done,
            'cancelled': status_counts.get('cancelled', 0),
            'overdue': overdue_count,
            'completion_rate': round((done / total) * 100, 2) if total > 0 else 0,
        }
