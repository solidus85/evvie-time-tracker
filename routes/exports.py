from flask import Blueprint, request, jsonify, current_app, send_file
from services.export_service import ExportService
from datetime import datetime
import io

bp = Blueprint('exports', __name__)

@bp.route('/pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.json
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({'error': 'Start and end dates required'}), 400
        
        service = ExportService(current_app.db)
        include_imported = bool(data.get('include_imported', True))

        pdf_buffer = service.generate_pdf_report(
            start_date=data['start_date'],
            end_date=data['end_date'],
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            include_imported=include_imported
        )
        
        filename = f"timesheet_{data['start_date']}_{data['end_date']}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({'error': 'Start and end dates required'}), 400
        
        service = ExportService(current_app.db)
        include_imported = bool(data.get('include_imported', True))

        csv_data = service.export_csv(
            start_date=data['start_date'],
            end_date=data['end_date'],
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            include_imported=include_imported
        )
        
        filename = f"timesheet_{data['start_date']}_{data['end_date']}.csv"
        return send_file(
            io.BytesIO(csv_data.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/json', methods=['POST'])
def export_json():
    try:
        data = request.json
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({'error': 'Start and end dates required'}), 400
        
        service = ExportService(current_app.db)
        include_imported = bool(data.get('include_imported', True))

        json_data = service.export_json(
            start_date=data['start_date'],
            end_date=data['end_date'],
            employee_id=data.get('employee_id'),
            child_id=data.get('child_id'),
            include_imported=include_imported
        )
        
        return jsonify(json_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
