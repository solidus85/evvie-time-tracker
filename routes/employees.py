from flask import Blueprint, request, jsonify, current_app
from services.employee_service import EmployeeService

bp = Blueprint('employees', __name__)

@bp.route('/', methods=['GET'])
def get_employees():
    try:
        service = EmployeeService(current_app.db)
        employees = service.get_all(active_only=request.args.get('active_only', 'false').lower() == 'true')
        return jsonify([dict(e) for e in employees])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:employee_id>', methods=['GET'])
def get_employee(employee_id):
    try:
        service = EmployeeService(current_app.db)
        employee = service.get_by_id(employee_id)
        if employee:
            return jsonify(dict(employee))
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/', methods=['POST'])
def create_employee():
    try:
        # Check content type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        # Try to get JSON data with error handling
        try:
            data = request.get_json(force=False)
        except Exception:
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        
        if not data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
            
        if not data.get('friendly_name') or not data.get('system_name'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = EmployeeService(current_app.db)
        employee_id = service.create(
            friendly_name=data['friendly_name'],
            system_name=data['system_name'],
            active=data.get('active', True),
            hidden=data.get('hidden', False)
        )
        return jsonify({'id': employee_id, 'message': 'Employee created'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id):
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
        service = EmployeeService(current_app.db)
        
        if service.update(employee_id, data):
            return jsonify({'message': 'Employee updated'})
        return jsonify({'error': 'Employee not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    try:
        service = EmployeeService(current_app.db)
        if service.deactivate(employee_id):
            return jsonify({'message': 'Employee deactivated'})
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
