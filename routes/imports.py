from flask import Blueprint, request, jsonify, current_app
from services.import_service import ImportService
import os

bp = Blueprint('imports', __name__)

@bp.route('/csv', methods=['POST'])
def import_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Invalid file type. Only CSV files allowed'}), 400
        
        file_size = len(file.read())
        file.seek(0)
        max_size = current_app.config.get('MAX_CSV_SIZE_MB', 10) * 1024 * 1024
        
        if file_size > max_size:
            return jsonify({'error': f'File too large. Maximum size: {max_size/1024/1024}MB'}), 400
        
        service = ImportService(current_app.db)
        result = service.import_csv(file)
        
        return jsonify({
            'message': 'CSV imported successfully',
            'imported': result['imported'],
            'duplicates': result['duplicates'],
            'errors': result['errors'],
            'warnings': result['warnings']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/validate', methods=['POST'])
def validate_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        service = ImportService(current_app.db)
        validation = service.validate_csv(file)
        
        return jsonify({
            'valid': validation['valid'],
            'rows': validation['rows'],
            'errors': validation['errors'],
            'warnings': validation['warnings']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500