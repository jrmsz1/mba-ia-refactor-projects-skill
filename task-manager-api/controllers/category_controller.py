from models.category import Category
from models.task import Task
from config.settings import Config
from controllers.task_controller import ValidationError, NotFoundError


class CategoryController:

    @staticmethod
    def list_categories():
        categories = Category.get_all()
        counts = Category.task_counts_by_category()
        result = []
        for category in categories:
            data = category.to_dict()
            data['task_count'] = counts.get(category.id, 0)
            result.append(data)
        return result

    @staticmethod
    def create_category(data):
        if not data:
            raise ValidationError('Dados inválidos')
        name = data.get('name')
        if not name:
            raise ValidationError('Nome é obrigatório')
        category = Category.create(
            name=name,
            description=data.get('description', ''),
            color=data.get('color', Config.DEFAULT_CATEGORY_COLOR),
        )
        return category.to_dict()

    @staticmethod
    def update_category(category_id, data):
        category = Category.get_by_id(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'color' in data:
            category.color = data['color']

        category.save()
        return category.to_dict()

    @staticmethod
    def delete_category(category_id):
        category = Category.get_by_id(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        category.delete()
