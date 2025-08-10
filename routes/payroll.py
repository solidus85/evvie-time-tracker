from flask import Blueprint, request, jsonify, current_app
from services.payroll_service import PayrollService
from datetime import datetime

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

@bp.route('/exclusions/<int:exclusion_id>', methods=['PUT'])
def update_exclusion_period(exclusion_id):
    try:
        data = request.json
        required = ['name', 'start_date', 'end_date']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = PayrollService(current_app.db)
        if service.update_exclusion_period(
            exclusion_id,
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            reason=data.get('reason')
        ):
            return jsonify({'message': 'Exclusion period updated'})
        return jsonify({'error': 'Exclusion period not found'}), 404
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