from datetime import datetime, timedelta

from models.task import Task
from models.user import User
from models.category import Category
from config.settings import Config
from controllers.task_controller import NotFoundError


PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


class ReportController:

    @staticmethod
    def summary_report():
        total_tasks = Task.total()
        total_users = User.query.count()
        total_categories = Category.query.count()

        status_counts = Task.count_by_status()
        priority_counts = Task.count_by_priority()
        overdue_tasks = Task.list_overdue()

        seven_days_ago = datetime.utcnow() - timedelta(days=Config.RECENT_ACTIVITY_DAYS)
        recent_tasks = Task.count_created_since(seven_days_ago)
        recent_done = Task.count_completed_since(seven_days_ago)

        users = User.get_all()
        per_user_stats = Task.stats_by_user()
        user_stats = []
        for user in users:
            stats = per_user_stats.get(user.id, {'total': 0, 'done': 0})
            total = stats['total']
            completed = stats['done']
            user_stats.append({
                'user_id': user.id,
                'user_name': user.name,
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': round((completed / total) * 100, 2) if total > 0 else 0,
            })

        return {
            'generated_at': str(datetime.utcnow()),
            'overview': {
                'total_tasks': total_tasks,
                'total_users': total_users,
                'total_categories': total_categories,
            },
            'tasks_by_status': {
                'pending': status_counts.get('pending', 0),
                'in_progress': status_counts.get('in_progress', 0),
                'done': status_counts.get('done', 0),
                'cancelled': status_counts.get('cancelled', 0),
            },
            'tasks_by_priority': {
                label: priority_counts.get(level, 0)
                for level, label in PRIORITY_LABELS.items()
            },
            'overdue': {
                'count': len(overdue_tasks),
                'tasks': [
                    {
                        'id': t.id,
                        'title': t.title,
                        'due_date': str(t.due_date),
                        'days_overdue': (datetime.utcnow() - t.due_date).days,
                    }
                    for t in overdue_tasks
                ],
            },
            'recent_activity': {
                'tasks_created_last_7_days': recent_tasks,
                'tasks_completed_last_7_days': recent_done,
            },
            'user_productivity': user_stats,
        }

    @staticmethod
    def user_report(user_id):
        user = User.get_by_id(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')

        tasks = Task.list_by_user(user_id)
        counters = {'total': len(tasks), 'done': 0, 'pending': 0,
                    'in_progress': 0, 'cancelled': 0,
                    'overdue': 0, 'high_priority': 0}

        for task in tasks:
            if task.status in counters:
                counters[task.status] += 1
            if task.priority <= 2:
                counters['high_priority'] += 1
            if task.is_overdue():
                counters['overdue'] += 1

        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
            },
            'statistics': {
                'total_tasks': counters['total'],
                'done': counters['done'],
                'pending': counters['pending'],
                'in_progress': counters['in_progress'],
                'cancelled': counters['cancelled'],
                'overdue': counters['overdue'],
                'high_priority': counters['high_priority'],
                'completion_rate': round((counters['done'] / counters['total']) * 100, 2)
                                   if counters['total'] > 0 else 0,
            },
        }
