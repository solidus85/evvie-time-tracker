from flask import Blueprint, request, jsonify, current_app
from services.payroll_service import PayrollService
from datetime import datetime, date, timedelta

bp = Blueprint('payroll', __name__)

@bp.route('/periods', methods=['GET'])
def get_payroll_periods():
    try:
        service = PayrollService(current_app.db)
        periods = service.get_all_periods()
        return jsonify([dict(p) for p in periods])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/current', methods=['GET'])
def get_current_period():
    try:
        service = PayrollService(current_app.db)
        period = service.get_current_period()
        if period:
            return jsonify(dict(period))
        return jsonify({'error': 'No current period found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/configure', methods=['POST'])
def configure_payroll_periods():
    try:
        data = request.json
        if not data.get('anchor_date'):
            return jsonify({'error': 'Anchor date required'}), 400
        
        service = PayrollService(current_app.db)
        service.configure_periods(data['anchor_date'])
        return jsonify({'message': 'Payroll periods configured'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/<int:period_id>', methods=['GET'])
def get_period_by_id(period_id):
    try:
        service = PayrollService(current_app.db)
        period = current_app.db.fetchone(
            "SELECT * FROM payroll_periods WHERE id = ?",
            (period_id,)
        )
        if period:
            return jsonify(dict(period))
        return jsonify({'error': 'Period not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/<int:period_id>/summary', methods=['GET'])
def get_period_summary(period_id):
    try:
        service = PayrollService(current_app.db)
        summary = service.get_period_summary(period_id)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/navigate', methods=['GET'])
def navigate_period():
    try:
        period_id = request.args.get('period_id', type=int)
        direction = request.args.get('direction', type=int)
        
        if not period_id or direction not in [-1, 1]:
            return jsonify({'error': 'Invalid parameters'}), 400
        
        service = PayrollService(current_app.db)
        period = service.navigate_period(period_id, direction)
        
        if period:
            return jsonify(dict(period))
        return jsonify({'error': 'No more periods in that direction'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions', methods=['GET'])
def get_exclusion_periods():
    try:
        service = PayrollService(current_app.db)
        exclusions = service.get_exclusion_periods(
            active_only=request.args.get('active_only', 'false').lower() == 'true'
        )
        return jsonify([dict(e) for e in exclusions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions', methods=['POST'])
def create_exclusion_period():
    try:
        data = request.json
        required = ['name', 'start_date', 'end_date']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = PayrollService(current_app.db)
        exclusion_id = service.create_exclusion_period(
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            reason=data.get('reason')
        )
        return jsonify({'id': exclusion_id, 'message': 'Exclusion period created'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/<int:exclusion_id>', methods=['GET'])
def get_exclusion_by_id(exclusion_id):
    try:
        exclusion = current_app.db.fetchone(
            "SELECT * FROM exclusion_periods WHERE id = ?",
            (exclusion_id,)
        )
        if exclusion:
            return jsonify(dict(exclusion))
        return jsonify({'error': 'Exclusion not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/<int:exclusion_id>', methods=['PUT'])
def update_exclusion_period(exclusion_id):
    try:
        data = request.json
        
        # Get existing exclusion to merge with updates
        existing = current_app.db.fetchone(
            "SELECT * FROM exclusion_periods WHERE id = ?",
            (exclusion_id,)
        )
        
        if not existing:
            return jsonify({'error': 'Exclusion period not found'}), 404
        
        # Merge existing data with updates (partial update support)
        updated_data = {
            'name': data.get('name', existing['name']),
            'start_date': data.get('start_date', existing['start_date']),
            'end_date': data.get('end_date', existing['end_date']),
            'start_time': data.get('start_time', existing['start_time']),
            'end_time': data.get('end_time', existing['end_time']),
            'employee_id': data.get('employee_id', existing['employee_id']),
            'child_id': data.get('child_id', existing['child_id']),
            'reason': data.get('reason', existing['reason'])
        }
        
        service = PayrollService(current_app.db)
        if service.update_exclusion_period(
            exclusion_id,
            name=updated_data['name'],
            start_date=updated_data['start_date'],
            end_date=updated_data['end_date'],
            start_time=updated_data['start_time'],
            end_time=updated_data['end_time'],
            employee_id=updated_data['employee_id'],
            child_id=updated_data['child_id'],
            reason=updated_data['reason']
        ):
            return jsonify({'message': 'Exclusion period updated'})
        return jsonify({'error': 'Update failed'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/<int:exclusion_id>', methods=['DELETE'])
def delete_exclusion_period(exclusion_id):
    try:
        service = PayrollService(current_app.db)
        if service.deactivate_exclusion_period(exclusion_id):
            return jsonify({'message': 'Exclusion period deactivated'})
        return jsonify({'error': 'Exclusion period not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/for-period', methods=['GET'])
def get_exclusions_for_period():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400
        
        service = PayrollService(current_app.db)
        exclusions = service.get_exclusions_for_period(start_date, end_date)
        return jsonify([dict(e) for e in exclusions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/preview', methods=['POST'])
def preview_bulk_exclusions():
    try:
        data = request.json
        required = ['days_of_week', 'weeks']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = PayrollService(current_app.db)
        dates = service.calculate_bulk_dates(
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            days_of_week=data['days_of_week'],
            weeks=data['weeks']
        )
        return jsonify(dates)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/exclusions/bulk', methods=['POST'])
def create_bulk_exclusions():
    try:
        data = request.json
        required = ['name_pattern', 'days_of_week', 'weeks']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = PayrollService(current_app.db)
        count = service.create_bulk_exclusions(
            name_pattern=data['name_pattern'],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            days_of_week=data['days_of_week'],
            weeks=data['weeks'],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            reason=data.get('reason')
        )
        return jsonify({'count': count, 'message': f'Created {count} exclusion periods'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/report/<int:period_id>', methods=['GET'])
def get_payroll_report(period_id):
    """Generate payroll report for a specific period"""
    try:
        service = PayrollService(current_app.db)
        
        # Get the period directly
        period = current_app.db.fetchone(
            "SELECT * FROM payroll_periods WHERE id = ?",
            (period_id,)
        )
        
        if not period:
            return jsonify({'error': 'Period not found'}), 404
        
        # Get all shifts for the period
        shifts = current_app.db.fetchall(
            """SELECT s.*, e.friendly_name as employee_name, c.name as child_name
               FROM shifts s
               JOIN employees e ON s.employee_id = e.id
               JOIN children c ON s.child_id = c.id
               WHERE s.date >= ? AND s.date <= ?
               ORDER BY e.friendly_name, s.date""",
            (period['start_date'], period['end_date'])
        )
        
        # Group by employee
        employees = {}
        for shift in shifts:
            emp_id = shift['employee_id']
            if emp_id not in employees:
                employees[emp_id] = {
                    'name': shift['employee_name'],
                    'shifts': [],
                    'total_hours': 0
                }
            
            # Calculate hours
            from datetime import datetime
            start = datetime.strptime(f"{shift['date']} {shift['start_time']}", '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(f"{shift['date']} {shift['end_time']}", '%Y-%m-%d %H:%M:%S')
            hours = (end - start).total_seconds() / 3600
            
            employees[emp_id]['shifts'].append(shift)
            employees[emp_id]['total_hours'] += hours
        
        return jsonify({
            'period': dict(period),
            'employees': list(employees.values()),
            'total_hours': sum(e['total_hours'] for e in employees.values())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/export', methods=['GET'])
def export_payroll():
    """Export payroll data using the same policy as export routes"""
    try:
        from services.export_service import ExportService
        format_type = request.args.get('format', 'json')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        include_imported = request.args.get('include_imported', 'true').lower() == 'true'

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400

        service = ExportService(current_app.db)

        if format_type == 'csv':
            data = service.export_csv(start_date, end_date, include_imported=include_imported)
            return data, 200, {'Content-Type': 'text/csv'}
        else:
            data = service.export_json(start_date, end_date, include_imported=include_imported)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/employee/<int:employee_id>/summary', methods=['GET'])
def get_employee_payroll_summary(employee_id):
    """Get payroll summary for a specific employee"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400
        
        # Get employee shifts
        shifts = current_app.db.fetchall(
            """SELECT s.*, c.name as child_name
               FROM shifts s
               JOIN children c ON s.child_id = c.id
               WHERE s.employee_id = ? AND s.date >= ? AND s.date <= ?
               ORDER BY s.date""",
            (employee_id, start_date, end_date)
        )
        
        # Calculate total hours
        total_hours = 0
        for shift in shifts:
            from datetime import datetime
            start = datetime.strptime(f"{shift['date']} {shift['start_time']}", '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(f"{shift['date']} {shift['end_time']}", '%Y-%m-%d %H:%M:%S')
            total_hours += (end - start).total_seconds() / 3600
        
        return jsonify({
            'employee_id': employee_id,
            'period': {'start_date': start_date, 'end_date': end_date},
            'shifts': [dict(s) for s in shifts],
            'total_hours': round(total_hours, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/overtime', methods=['GET'])
def get_overtime_report():
    """Get overtime report for all employees"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        overtime_threshold = float(request.args.get('threshold', 40))
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required'}), 400
        
        # Get all employees with their hours
        employees = current_app.db.fetchall(
            """SELECT e.id, e.friendly_name, 
                      SUM((julianday(s.date || ' ' || s.end_time) - 
                           julianday(s.date || ' ' || s.start_time)) * 24) as total_hours
               FROM employees e
               LEFT JOIN shifts s ON e.id = s.employee_id
               WHERE s.date >= ? AND s.date <= ?
               GROUP BY e.id, e.friendly_name
               HAVING total_hours > ?""",
            (start_date, end_date, overtime_threshold)
        )
        
        overtime_report = []
        for emp in employees:
            if emp['total_hours']:
                overtime_hours = max(0, emp['total_hours'] - overtime_threshold)
                overtime_report.append({
                    'employee_id': emp['id'],
                    'employee_name': emp['friendly_name'],
                    'total_hours': round(emp['total_hours'], 2),
                    'regular_hours': min(overtime_threshold, emp['total_hours']),
                    'overtime_hours': round(overtime_hours, 2)
                })
        
        return jsonify(overtime_report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/<int:period_id>/next', methods=['GET'])
def get_next_period(period_id):
    """Get the next payroll period"""
    try:
        service = PayrollService(current_app.db)
        next_period = service.navigate_period(period_id, 1)
        
        if next_period:
            return jsonify(dict(next_period))
        return jsonify({'error': 'No next period found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/<int:period_id>/previous', methods=['GET'])
def get_previous_period(period_id):
    """Get the previous payroll period"""
    try:
        service = PayrollService(current_app.db)
        prev_period = service.navigate_period(period_id, -1)
        
        if prev_period:
            return jsonify(dict(prev_period))
        return jsonify({'error': 'No previous period found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/periods/<int:period_id>/approve', methods=['POST'])
def approve_period(period_id):
    """Approve a payroll period (placeholder)"""
    try:
        data = request.json
        approved_by = data.get('approved_by', 'System')
        
        # In a real system, this would update the period status
        # For now, just return success
        return jsonify({
            'period_id': period_id,
            'status': 'approved',
            'approved_by': approved_by,
            'approved_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/calculate', methods=['POST'])
def calculate_payroll():
    """Calculate payroll for an employee"""
    try:
        data = request.json
        employee_id = data.get('employee_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not all([employee_id, start_date, end_date]):
            return jsonify({'error': 'employee_id, start_date, and end_date required'}), 400
        
        # Get employee rate
        employee = current_app.db.fetchone(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        )
        
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Get total hours
        result = current_app.db.fetchone(
            """SELECT SUM((julianday(date || ' ' || end_time) - 
                          julianday(date || ' ' || start_time)) * 24) as total_hours
               FROM shifts
               WHERE employee_id = ? AND date >= ? AND date <= ?""",
            (employee_id, start_date, end_date)
        )
        
        total_hours = result['total_hours'] if result and result['total_hours'] else 0
        hourly_rate = employee['hourly_rate'] if employee and employee['hourly_rate'] else 0
        total_pay = total_hours * hourly_rate
        
        return jsonify({
            'employee_id': employee_id,
            'employee_name': employee['friendly_name'],
            'period': {'start_date': start_date, 'end_date': end_date},
            'total_hours': round(total_hours, 2),
            'hourly_rate': hourly_rate,
            'total_pay': round(total_pay, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
