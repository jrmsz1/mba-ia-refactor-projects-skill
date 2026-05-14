from flask import Blueprint, request, jsonify

from controllers.task_controller import TaskController

task_bp = Blueprint('tasks', __name__)


@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(TaskController.list_tasks()), 200


@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks():
    result = TaskController.search_tasks(
        query=request.args.get('q', ''),
        status=request.args.get('status', ''),
        priority=request.args.get('priority', ''),
        user_id=request.args.get('user_id', ''),
    )
    return jsonify(result), 200


@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    return jsonify(TaskController.task_stats()), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    return jsonify(TaskController.get_task(task_id)), 200


@task_bp.route('/tasks', methods=['POST'])
def create_task():
    result = TaskController.create_task(request.get_json(silent=True))
    return jsonify(result), 201


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    result = TaskController.update_task(task_id, request.get_json(silent=True))
    return jsonify(result), 200


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    TaskController.delete_task(task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200
