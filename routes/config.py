from flask import Blueprint, request, jsonify, current_app
from services.config_service import ConfigService

bp = Blueprint('config', __name__)

@bp.route('/hour-limits', methods=['GET'])
def get_hour_limits():
    try:
        service = ConfigService(current_app.db)
        limits = service.get_all_hour_limits(
            active_only=request.args.get('active_only', 'false').lower() == 'true'
        )
        return jsonify([dict(l) for l in limits])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hour-limits', methods=['POST'])
def create_hour_limit():
    try:
        data = request.json
        # Support both old and new field names for compatibility
        if 'max_hours_per_period' in data and 'max_hours_per_week' not in data:
            data['max_hours_per_week'] = data['max_hours_per_period'] / 2.0  # Convert period to week
        
        required = ['employee_id', 'child_id', 'max_hours_per_week']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = ConfigService(current_app.db)
        limit_id = service.create_hour_limit(
            employee_id=data['employee_id'],
            child_id=data['child_id'],
            max_hours_per_week=data['max_hours_per_week'],
            alert_threshold=data.get('alert_threshold')
        )
        return jsonify({'id': limit_id, 'message': 'Hour limit created'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hour-limits/<int:limit_id>', methods=['PUT'])
def update_hour_limit(limit_id):
    try:
        data = request.json
        service = ConfigService(current_app.db)
        
        if service.update_hour_limit(limit_id, data):
            return jsonify({'message': 'Hour limit updated'})
        return jsonify({'error': 'Hour limit not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/hour-limits/<int:limit_id>', methods=['DELETE'])
def delete_hour_limit(limit_id):
    try:
        service = ConfigService(current_app.db)
        if service.deactivate_hour_limit(limit_id):
            return jsonify({'message': 'Hour limit deactivated'})
        return jsonify({'error': 'Hour limit not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/settings', methods=['GET'])
def get_settings():
    try:
        service = ConfigService(current_app.db)
        settings = service.get_app_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/settings', methods=['PUT'])
def update_settings():
    try:
        data = request.json
        service = ConfigService(current_app.db)
        service.update_app_settings(data)
        return jsonify({'message': 'Settings updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500