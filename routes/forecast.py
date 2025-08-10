from flask import Blueprint, request, jsonify, current_app
from services.forecast_service import ForecastService
from datetime import datetime

bp = Blueprint('forecast', __name__)

@bp.route('/available-hours', methods=['GET'])
def get_available_hours():
    try:
        child_id = request.args.get('child_id', type=int)
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')
        
        if not all([child_id, period_start, period_end]):
            return jsonify({'error': 'child_id, period_start, and period_end required'}), 400
        
        service = ForecastService(current_app.db)
        available = service.get_available_hours(child_id, period_start, period_end)
        
        return jsonify(available)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/patterns', methods=['GET'])
def get_historical_patterns():
    try:
        child_id = request.args.get('child_id', type=int)
        lookback_days = request.args.get('lookback_days', 90, type=int)
        
        if not child_id:
            return jsonify({'error': 'child_id required'}), 400
        
        service = ForecastService(current_app.db)
        patterns = service.get_historical_patterns(child_id, lookback_days)
        
        return jsonify(patterns)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/projections', methods=['GET'])
def get_projections():
    try:
        child_id = request.args.get('child_id', type=int)
        projection_days = request.args.get('projection_days', 30, type=int)
        
        if not child_id:
            return jsonify({'error': 'child_id required'}), 400
        
        service = ForecastService(current_app.db)
        projection = service.project_hours(child_id, projection_days)
        
        return jsonify(projection)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/recommendations', methods=['GET'])
def get_allocation_recommendations():
    try:
        period_id = request.args.get('period_id', type=int)
        
        if not period_id:
            return jsonify({'error': 'period_id required'}), 400
        
        service = ForecastService(current_app.db)
        recommendations = service.get_allocation_recommendations(period_id)
        
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/summary', methods=['GET'])
def get_forecast_summary():
    try:
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')
        
        if not all([period_start, period_end]):
            # Try to get current period
            from services.payroll_service import PayrollService
            payroll_service = PayrollService(current_app.db)
            current_period = payroll_service.get_current_period()
            
            if current_period:
                period_start = current_period['start_date']
                period_end = current_period['end_date']
            else:
                return jsonify({'error': 'period_start and period_end required, or configure payroll periods'}), 400
        
        service = ForecastService(current_app.db)
        summary = service.get_forecast_summary(period_start, period_end)
        
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/available-hours/batch', methods=['POST'])
def get_available_hours_batch():
    """Get available hours for multiple children at once"""
    try:
        data = request.json
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        child_ids = data.get('child_ids', [])
        
        if not all([period_start, period_end]):
            return jsonify({'error': 'period_start and period_end required'}), 400
        
        service = ForecastService(current_app.db)
        results = []
        
        # If no child_ids specified, get all active children
        if not child_ids:
            children = current_app.db.fetchall(
                "SELECT id FROM children WHERE active = 1"
            )
            child_ids = [c['id'] for c in children]
        
        for child_id in child_ids:
            available = service.get_available_hours(child_id, period_start, period_end)
            # Get child name for better display
            child = current_app.db.fetchone(
                "SELECT name FROM children WHERE id = ?",
                (child_id,)
            )
            if child:
                available['child_name'] = child['name']
            results.append(available)
        
        return jsonify({
            'period_start': period_start,
            'period_end': period_end,
            'children': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/projections/batch', methods=['POST'])
def get_projections_batch():
    """Get projections for multiple children at once"""
    try:
        data = request.json
        projection_days = data.get('projection_days', 30)
        child_ids = data.get('child_ids', [])
        
        service = ForecastService(current_app.db)
        results = []
        
        # If no child_ids specified, get all active children
        if not child_ids:
            children = current_app.db.fetchall(
                "SELECT id FROM children WHERE active = 1"
            )
            child_ids = [c['id'] for c in children]
        
        for child_id in child_ids:
            projection = service.project_hours(child_id, projection_days)
            # Get child name for better display
            child = current_app.db.fetchone(
                "SELECT name FROM children WHERE id = ?",
                (child_id,)
            )
            if child:
                projection['child_name'] = child['name']
            results.append(projection)
        
        return jsonify({
            'projection_days': projection_days,
            'children': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500