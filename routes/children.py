from flask import Blueprint, request, jsonify, current_app
from services.child_service import ChildService

bp = Blueprint('children', __name__)

@bp.route('/', methods=['GET'])
def get_children():
    try:
        service = ChildService(current_app.db)
        children = service.get_all(active_only=request.args.get('active_only', 'false').lower() == 'true')
        return jsonify([dict(c) for c in children])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:child_id>', methods=['GET'])
def get_child(child_id):
    try:
        service = ChildService(current_app.db)
        child = service.get_by_id(child_id)
        if child:
            return jsonify(dict(child))
        return jsonify({'error': 'Child not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/', methods=['POST'])
def create_child():
    try:
        # Enforce JSON Content-Type and parse
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        try:
            data = request.get_json(force=False)
        except Exception:
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        if not data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        if not data.get('name') or not data.get('code'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = ChildService(current_app.db)
        child_id = service.create(
            name=data['name'],
            code=data['code'],
            active=data.get('active', True)
        )
        return jsonify({'id': child_id, 'message': 'Child created'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:child_id>', methods=['PUT'])
def update_child(child_id):
    try:
        # Enforce JSON Content-Type and parse
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        try:
            data = request.get_json(force=False)
        except Exception:
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        if not isinstance(data, dict):
            return jsonify({'error': 'Request body must be a JSON object'}), 400
        service = ChildService(current_app.db)
        
        if service.update(child_id, data):
            return jsonify({'message': 'Child updated'})
        return jsonify({'error': 'Child not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:child_id>', methods=['DELETE'])
def delete_child(child_id):
    try:
        service = ChildService(current_app.db)
        if service.deactivate(child_id):
            return jsonify({'message': 'Child deactivated'})
        return jsonify({'error': 'Child not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
