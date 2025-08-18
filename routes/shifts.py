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
        
        # Convert IDs to integers (they come as strings from frontend)
        try:
            employee_id = int(data['employee_id'])
            child_id = int(data['child_id'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid employee or child ID'}), 400
        
        # Validate date is a real date
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format or non-existent date'}), 400
        
        service = ShiftService(current_app.db)
        
        # Check if employee and child exist
        employee = current_app.db.fetchone(
            "SELECT id FROM employees WHERE id = ?", (employee_id,)
        )
        if not employee:
            return jsonify({'error': f'Employee with ID {employee_id} not found'}), 404
        
        child = current_app.db.fetchone(
            "SELECT id FROM children WHERE id = ?", (child_id,)
        )
        if not child:
            return jsonify({'error': f'Child with ID {child_id} not found'}), 404
        
        # Validate the shift first - this will raise ValueError for conflicts
        try:
            warnings = service.validate_shift(
                employee_id=employee_id,
                child_id=child_id,
                date=data['date'],
                start_time=data['start_time'],
                end_time=data['end_time']
            )
        except ValueError as e:
            # Return conflict errors with clear messaging
            error_msg = str(e)
            current_app.logger.info(f"Validation error: {error_msg}")
            # Check for overlapping (more generic to catch "an overlapping shift")
            if 'overlapping' in error_msg.lower():
                return jsonify({
                    'error': 'Shift Conflict',
                    'message': error_msg,
                    'type': 'overlap'
                }), 409  # 409 Conflict is more appropriate than 400
            elif 'excluded' in error_msg.lower():
                return jsonify({
                    'error': 'Exclusion Period',
                    'message': error_msg,
                    'type': 'exclusion'
                }), 409
            else:
                return jsonify({'error': error_msg}), 400
        
        # Create the shift if validation passed
        try:
            shift_id = service.create(
                employee_id=employee_id,
                child_id=child_id,
                date=data['date'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                service_code=data.get('service_code'),
                status=data.get('status', 'new')
            )
        except Exception as e:
            # Handle database errors (like unique constraints and foreign key violations)
            error_msg = str(e)
            current_app.logger.error(f"Failed to create shift: {error_msg}")
            
            if 'FOREIGN KEY constraint failed' in error_msg:
                return jsonify({
                    'error': 'Invalid reference',
                    'message': 'The specified employee or child does not exist.'
                }), 400
            elif 'UNIQUE constraint failed' in error_msg:
                return jsonify({
                    'error': 'Duplicate shift',
                    'message': 'A shift with these details already exists.'
                }), 409
            else:
                return jsonify({
                    'error': 'Failed to create shift',
                    'message': 'An unexpected error occurred while saving the shift. Please try again.'
                }), 500
        
        response = {'id': shift_id, 'message': 'Shift created successfully'}
        if warnings:
            response['warnings'] = warnings
        
        return jsonify(response), 201
    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_shift: {str(e)}")
        return jsonify({
            'error': 'Unexpected error',
            'message': 'An unexpected error occurred. Please try again.'
        }), 500

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

@bp.route('/auto-generate', methods=['POST'])
def auto_generate_shifts():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not data.get('child_id') or not data.get('employee_id') or not data.get('date'):
            return jsonify({'error': 'Missing required fields: child_id, employee_id, date'}), 400
        
        service = ShiftService(current_app.db)
        
        # Auto-generate shifts
        result = service.auto_generate_shifts(
            child_id=data['child_id'],
            employee_id=data['employee_id'],
            date=data['date']
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500