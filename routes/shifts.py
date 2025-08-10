from flask import Blueprint, request, jsonify, current_app
from services.shift_service import ShiftService
from datetime import datetime

bp = Blueprint('shifts', __name__)

@bp.route('/', methods=['GET'])
def get_shifts():
    try:
        service = ShiftService(current_app.db)
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        child_id = request.args.get('child_id')
        
        shifts = service.get_shifts(
            start_date=start_date,
            end_date=end_date,
            employee_id=employee_id,
            child_id=child_id
        )
        return jsonify([dict(s) for s in shifts])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:shift_id>', methods=['GET'])
def get_shift(shift_id):
    try:
        service = ShiftService(current_app.db)
        shift = service.get_by_id(shift_id)
        if shift:
            return jsonify(dict(shift))
        return jsonify({'error': 'Shift not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/', methods=['POST'])
def create_shift():
    try:
        data = request.json
        required = ['employee_id', 'child_id', 'date', 'start_time', 'end_time']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = ShiftService(current_app.db)
        
        warnings = service.validate_shift(
            employee_id=data['employee_id'],
            child_id=data['child_id'],
            date=data['date'],
            start_time=data['start_time'],
            end_time=data['end_time']
        )
        
        shift_id = service.create(
            employee_id=data['employee_id'],
            child_id=data['child_id'],
            date=data['date'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            service_code=data.get('service_code'),
            status=data.get('status', 'new')
        )
        
        response = {'id': shift_id, 'message': 'Shift created'}
        if warnings:
            response['warnings'] = warnings
        
        return jsonify(response), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:shift_id>', methods=['PUT'])
def update_shift(shift_id):
    try:
        data = request.json
        service = ShiftService(current_app.db)
        
        shift = service.get_by_id(shift_id)
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404
        
        if shift['is_imported']:
            return jsonify({'error': 'Cannot edit imported shifts'}), 403
        
        warnings = []
        if any(field in data for field in ['date', 'start_time', 'end_time']):
            warnings = service.validate_shift(
                employee_id=data.get('employee_id', shift['employee_id']),
                child_id=data.get('child_id', shift['child_id']),
                date=data.get('date', shift['date']),
                start_time=data.get('start_time', shift['start_time']),
                end_time=data.get('end_time', shift['end_time']),
                exclude_shift_id=shift_id
            )
        
        if service.update(shift_id, data):
            response = {'message': 'Shift updated'}
            if warnings:
                response['warnings'] = warnings
            return jsonify(response)
        
        return jsonify({'error': 'Update failed'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:shift_id>', methods=['DELETE'])
def delete_shift(shift_id):
    try:
        service = ShiftService(current_app.db)
        
        shift = service.get_by_id(shift_id)
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404
        
        if shift['is_imported']:
            return jsonify({'error': 'Cannot delete imported shifts'}), 403
        
        if service.delete(shift_id):
            return jsonify({'message': 'Shift deleted'})
        return jsonify({'error': 'Delete failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500