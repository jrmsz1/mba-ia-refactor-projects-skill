from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from models.database import db
from config.settings import TERMINAL_TASK_STATUSES


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    category = db.relationship('Category', backref='tasks')

    def is_overdue(self):
        if not self.due_date:
            return False
        if self.status in TERMINAL_TASK_STATUSES:
            return False
        return self.due_date < datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_dict_with_overdue(self):
        data = self.to_dict()
        data['overdue'] = self.is_overdue()
        return data

    @classmethod
    def get_all_with_relations(cls):
        return cls.query.options(
            joinedload(cls.user), joinedload(cls.category)
        ).all()

    @classmethod
    def get_by_id(cls, task_id):
        return cls.query.get(task_id)

    @classmethod
    def search(cls, query=None, status=None, priority=None, user_id=None):
        q = cls.query
        if query:
            like = f'%{query}%'
            q = q.filter(db.or_(cls.title.like(like), cls.description.like(like)))
        if status:
            q = q.filter(cls.status == status)
        if priority is not None:
            q = q.filter(cls.priority == priority)
        if user_id is not None:
            q = q.filter(cls.user_id == user_id)
        return q.all()

    @classmethod
    def list_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def count_by_status(cls):
        rows = db.session.query(cls.status, func.count(cls.id)).group_by(cls.status).all()
        return {status: count for status, count in rows}

    @classmethod
    def count_by_priority(cls):
        rows = db.session.query(cls.priority, func.count(cls.id)).group_by(cls.priority).all()
        return {priority: count for priority, count in rows}

    @classmethod
    def total(cls):
        return cls.query.count()

    @classmethod
    def list_overdue(cls):
        now = datetime.utcnow()
        return cls.query.filter(
            cls.due_date.isnot(None),
            cls.due_date < now,
            ~cls.status.in_(TERMINAL_TASK_STATUSES),
        ).all()

    @classmethod
    def count_created_since(cls, since):
        return cls.query.filter(cls.created_at >= since).count()

    @classmethod
    def count_completed_since(cls, since):
        return cls.query.filter(cls.status == 'done', cls.updated_at >= since).count()

    @classmethod
    def stats_by_user(cls):
        rows = db.session.query(
            cls.user_id, cls.status, func.count(cls.id)
        ).group_by(cls.user_id, cls.status).all()
        result = {}
        for user_id, status, count in rows:
            bucket = result.setdefault(user_id, {'total': 0, 'done': 0})
            bucket['total'] += count
            if status == 'done':
                bucket['done'] += count
        return result

    @classmethod
    def create(cls, **fields):
        task = cls(**fields)
        db.session.add(task)
        db.session.commit()
        return task

    def save(self):
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()
