from datetime import datetime
from sqlalchemy import func

from models.database import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default='#000000')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': str(self.created_at),
        }

    @classmethod
    def get_all(cls):
        return cls.query.all()

    @classmethod
    def get_by_id(cls, category_id):
        return cls.query.get(category_id)

    @classmethod
    def task_counts_by_category(cls):
        from models.task import Task
        rows = db.session.query(Task.category_id, func.count(Task.id)).group_by(Task.category_id).all()
        return {category_id: count for category_id, count in rows}

    @classmethod
    def create(cls, name, description='', color='#000000'):
        category = cls(name=name, description=description, color=color)
        db.session.add(category)
        db.session.commit()
        return category

    def save(self):
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()
