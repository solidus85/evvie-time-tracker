from flask import Blueprint, request, jsonify, current_app
from services.budget_service import BudgetService
from services.pdf_budget_parser import PDFBudgetParser
from datetime import datetime
import os
import tempfile

bp = Blueprint('budget', __name__)

# Child Budget Endpoints
@bp.route('/children', methods=['GET'])
def get_child_budgets():
    try:
        service = BudgetService(current_app.db)
        child_id = request.args.get('child_id', type=int)
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        budgets = service.get_child_budgets(child_id, active_only)
        return jsonify([dict(b) for b in budgets])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/children', methods=['POST'])
def create_child_budget():
    try:
        data = request.json
        required = ['child_id', 'period_start', 'period_end']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = BudgetService(current_app.db)
        budget_id = service.create_child_budget(
            child_id=data['child_id'],
            period_start=data['period_start'],
            period_end=data['period_end'],
            budget_amount=data.get('budget_amount'),
            budget_hours=data.get('budget_hours'),
            notes=data.get('notes')
        )
        
        return jsonify({'id': budget_id, 'message': 'Budget created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/children/<int:budget_id>', methods=['PUT'])
def update_child_budget(budget_id):
    try:
        data = request.json
        service = BudgetService(current_app.db)
        
        service.update_child_budget(
            budget_id=budget_id,
            budget_amount=data.get('budget_amount'),
            budget_hours=data.get('budget_hours'),
            notes=data.get('notes')
        )
        
        return jsonify({'message': 'Budget updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/children/<int:budget_id>', methods=['DELETE'])
def delete_child_budget(budget_id):
    try:
        service = BudgetService(current_app.db)
        service.delete_child_budget(budget_id)
        return jsonify({'message': 'Budget deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Employee Rate Endpoints
@bp.route('/rates', methods=['GET'])
def get_employee_rates():
    try:
        service = BudgetService(current_app.db)
        employee_id = request.args.get('employee_id', type=int)
        as_of_date = request.args.get('as_of_date')
        
        rates = service.get_employee_rates(employee_id, as_of_date)
        return jsonify([dict(r) for r in rates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/rates', methods=['POST'])
def create_employee_rate():
    try:
        data = request.json
        required = ['employee_id', 'hourly_rate', 'effective_date']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = BudgetService(current_app.db)
        rate_id = service.create_employee_rate(
            employee_id=data['employee_id'],
            hourly_rate=data['hourly_rate'],
            effective_date=data['effective_date'],
            end_date=data.get('end_date'),
            notes=data.get('notes')
        )
        
        return jsonify({'id': rate_id, 'message': 'Rate created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/rates/<int:rate_id>', methods=['PUT'])
def update_employee_rate(rate_id):
    try:
        data = request.json
        service = BudgetService(current_app.db)
        
        service.update_employee_rate(
            rate_id=rate_id,
            hourly_rate=data.get('hourly_rate'),
            end_date=data.get('end_date'),
            notes=data.get('notes')
        )
        
        return jsonify({'message': 'Rate updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Budget Allocation Endpoints
@bp.route('/allocations', methods=['GET'])
def get_allocations():
    try:
        service = BudgetService(current_app.db)
        period_id = request.args.get('period_id', type=int)
        if not period_id:
            return jsonify({'error': 'Period ID required'}), 400
        
        child_id = request.args.get('child_id', type=int)
        employee_id = request.args.get('employee_id', type=int)
        
        allocations = service.get_allocations(period_id, child_id, employee_id)
        return jsonify([dict(a) for a in allocations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/allocations', methods=['POST'])
def create_allocation():
    try:
        data = request.json
        required = ['child_id', 'employee_id', 'period_id', 'allocated_hours']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        service = BudgetService(current_app.db)
        allocation_id = service.create_allocation(
            child_id=data['child_id'],
            employee_id=data['employee_id'],
            period_id=data['period_id'],
            allocated_hours=data['allocated_hours'],
            notes=data.get('notes')
        )
        
        return jsonify({'id': allocation_id, 'message': 'Allocation created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Budget Analysis Endpoints
@bp.route('/utilization', methods=['GET'])
def get_budget_utilization():
    try:
        child_id = request.args.get('child_id', type=int)
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')
        
        if not all([child_id, period_start, period_end]):
            return jsonify({'error': 'child_id, period_start, and period_end required'}), 400
        
        service = BudgetService(current_app.db)
        utilization = service.get_budget_utilization(child_id, period_start, period_end)
        
        if not utilization:
            return jsonify({'error': 'No budget found for specified period'}), 404
        
        return jsonify(utilization)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Import Endpoint
@bp.route('/import', methods=['POST'])
def import_budgets():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400
        
        service = BudgetService(current_app.db)
        result = service.import_budgets_csv(file)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PDF Budget Report Endpoints
@bp.route('/upload-report', methods=['POST'])
def upload_budget_report():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        try:
            # Parse the PDF
            parser = PDFBudgetParser(current_app.db)
            report_data = parser.parse_spending_report(temp_path)
            
            # Save to database
            report_id = parser.save_budget_report(report_data, file.filename)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return jsonify({
                'success': True,
                'report_id': report_id,
                'summary': {
                    'client': report_data['report_info'].get('client_name', 'Unknown'),
                    'total_budget': report_data['budget_summary'].get('total_budgeted', 0),
                    'total_spent': report_data['budget_summary'].get('total_spent', 0),
                    'utilization': report_data['budget_summary'].get('utilization_percentage', 0)
                }
            })
        finally:
            # Ensure temp file is deleted
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/reports', methods=['GET'])
def get_budget_reports():
    try:
        parser = PDFBudgetParser(current_app.db)
        child_id = request.args.get('child_id', type=int)
        
        reports = parser.get_budget_reports(child_id)
        
        # Convert Row objects to dicts and handle JSON data
        report_list = []
        for report in reports:
            report_dict = dict(report)
            if report_dict.get('report_data'):
                import json
                report_dict['report_data'] = json.loads(report_dict['report_data'])
            report_list.append(report_dict)
        
        return jsonify(report_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/reports/<int:report_id>', methods=['GET'])
def get_budget_report(report_id):
    try:
        parser = PDFBudgetParser(current_app.db)
        report = parser.get_report_by_id(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        return jsonify(dict(report))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/reports/<int:report_id>', methods=['DELETE'])
def delete_budget_report(report_id):
    try:
        parser = PDFBudgetParser(current_app.db)
        parser.delete_budget_report(report_id)
        return jsonify({'success': True, 'message': 'Report deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500