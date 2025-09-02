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

def _validate_time_str(value):
    try:
        datetime.strptime(value, '%H:%M:%S')
        return True
    except Exception:
        return False

@bp.route('/', methods=['POST'])
def create_shift():
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

        required = ['employee_id', 'child_id', 'date', 'start_time', 'end_time']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate time formats strictly
        if not _validate_time_str(data['start_time']):
            return jsonify({'error': "Invalid start_time format. Use 'HH:MM:SS'"}), 400
        if not _validate_time_str(data['end_time']):
            return jsonify({'error': "Invalid end_time format. Use 'HH:MM:SS'"}), 400
        
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
        # Enforce JSON Content-Type and parse
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        try:
            data = request.get_json(force=False)
        except Exception:
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        if not isinstance(data, dict):
            return jsonify({'error': 'Request body must be a JSON object'}), 400
        service = ShiftService(current_app.db)
        
        shift = service.get_by_id(shift_id)
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404
        
        if shift['is_imported']:
            return jsonify({'error': 'Cannot edit imported shifts'}), 403
        
        # Validate provided fields
        if 'date' in data:
            try:
                datetime.strptime(data['date'], '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        if 'start_time' in data and not _validate_time_str(data['start_time']):
            return jsonify({'error': "Invalid start_time format. Use 'HH:MM:SS'"}), 400
        if 'end_time' in data and not _validate_time_str(data['end_time']):
            return jsonify({'error': "Invalid end_time format. Use 'HH:MM:SS'"}), 400

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

@bp.route('/overlaps', methods=['GET'])
def get_overlaps():
    try:
        service = ShiftService(current_app.db)
        
        # Get all shifts and find overlaps
        shifts = service.get_shifts()
        overlaps = []
        
        from collections import defaultdict
        
        # Group shifts by employee and date for employee overlap detection
        shifts_by_employee_date = defaultdict(list)
        # Group shifts by child and date for child overlap detection
        shifts_by_child_date = defaultdict(list)
        
        for shift in shifts:
            employee_key = (shift['employee_id'], shift['date'])
            shifts_by_employee_date[employee_key].append(shift)
            
            child_key = (shift['child_id'], shift['date'])
            shifts_by_child_date[child_key].append(shift)
        
        # Find employee overlaps (same employee, overlapping times)
        for (employee_id, date), employee_shifts in shifts_by_employee_date.items():
            if len(employee_shifts) < 2:
                continue
                
            # Sort shifts by start time
            employee_shifts.sort(key=lambda s: s['start_time'])
            
            # Check each pair of shifts for overlap
            for i in range(len(employee_shifts)):
                for j in range(i + 1, len(employee_shifts)):
                    shift1 = employee_shifts[i]
                    shift2 = employee_shifts[j]
                    
                    # Overlap if NOT (end1 <= start2 OR start1 >= end2)
                    if not (shift1['end_time'] <= shift2['start_time'] or shift1['start_time'] >= shift2['end_time']):
                        overlap = {
                            'date': date,
                            'overlap_type': 'employee',
                            'employee_id': employee_id,
                            'employee_name': shift1['employee_name'],
                            'child_id': None,
                            'child_name': None,
                            'shift1_id': shift1['id'],
                            'shift1_start': shift1['start_time'],
                            'shift1_end': shift1['end_time'],
                            'shift1_employee': shift1['employee_name'],
                            'shift1_child': shift1['child_name'],
                            'shift1_imported': shift1['is_imported'] if 'is_imported' in shift1.keys() else False,
                            'shift2_id': shift2['id'],
                            'shift2_start': shift2['start_time'],
                            'shift2_end': shift2['end_time'],
                            'shift2_employee': shift2['employee_name'],
                            'shift2_child': shift2['child_name'],
                            'shift2_imported': shift2['is_imported'] if 'is_imported' in shift2.keys() else False
                        }
                        overlaps.append(overlap)
        
        # Find child overlaps (same child, different employees, overlapping times)
        for (child_id, date), child_shifts in shifts_by_child_date.items():
            if len(child_shifts) < 2:
                continue
                
            # Sort shifts by start time
            child_shifts.sort(key=lambda s: s['start_time'])
            
            # Check each pair of shifts for overlap
            for i in range(len(child_shifts)):
                for j in range(i + 1, len(child_shifts)):
                    shift1 = child_shifts[i]
                    shift2 = child_shifts[j]
                    
                    # Skip if same employee (already handled above)
                    if shift1['employee_id'] == shift2['employee_id']:
                        continue
                    
                    # Overlap if NOT (end1 <= start2 OR start1 >= end2)
                    if not (shift1['end_time'] <= shift2['start_time'] or shift1['start_time'] >= shift2['end_time']):
                        overlap = {
                            'date': date,
                            'overlap_type': 'child',
                            'employee_id': None,
                            'employee_name': None,
                            'child_id': child_id,
                            'child_name': shift1['child_name'],
                            'shift1_id': shift1['id'],
                            'shift1_start': shift1['start_time'],
                            'shift1_end': shift1['end_time'],
                            'shift1_employee': shift1['employee_name'],
                            'shift1_child': shift1['child_name'],
                            'shift1_imported': shift1['is_imported'] if 'is_imported' in shift1.keys() else False,
                            'shift2_id': shift2['id'],
                            'shift2_start': shift2['start_time'],
                            'shift2_end': shift2['end_time'],
                            'shift2_employee': shift2['employee_name'],
                            'shift2_child': shift2['child_name'],
                            'shift2_imported': shift2['is_imported'] if 'is_imported' in shift2.keys() else False
                        }
                        overlaps.append(overlap)
        
        # Sort overlaps by date descending
        overlaps.sort(key=lambda o: o['date'], reverse=True)
        
        return jsonify(overlaps)
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
