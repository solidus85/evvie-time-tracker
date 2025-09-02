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
            'replaced': result.get('replaced', 0),
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

@bp.route('/batch-csv', methods=['POST'])
def batch_import_csv():
    try:
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        service = ImportService(current_app.db)
        max_size = current_app.config.get('MAX_CSV_SIZE_MB', 10) * 1024 * 1024
        
        all_results = []
        total_imported = 0
        total_duplicates = 0
        all_errors = []
        all_warnings = []
        
        for file_index, file in enumerate(files, 1):
            if file.filename == '':
                continue
                
            if not file.filename.lower().endswith('.csv'):
                all_errors.append(f"File {file.filename}: Invalid file type. Only CSV files allowed")
                continue
            
            file_size = len(file.read())
            file.seek(0)
            
            if file_size > max_size:
                all_errors.append(f"File {file.filename}: Too large. Maximum size: {max_size/1024/1024}MB")
                continue
            
            try:
                result = service.import_csv(file)
                total_imported += result['imported']
                total_duplicates += result['duplicates']
                
                # Prefix errors and warnings with filename
                for error in result['errors']:
                    all_errors.append(f"File {file.filename} - {error}")
                for warning in result['warnings']:
                    all_warnings.append(f"File {file.filename} - {warning}")
                    
                all_results.append({
                    'filename': file.filename,
                    'imported': result['imported'],
                    'duplicates': result['duplicates']
                })
            except Exception as e:
                all_errors.append(f"File {file.filename}: {str(e)}")
        
        return jsonify({
            'message': f'Processed {len(files)} file(s)',
            'total_imported': total_imported,
            'total_duplicates': total_duplicates,
            'file_results': all_results,
            'errors': all_errors,
            'warnings': all_warnings
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/batch-validate', methods=['POST'])
def batch_validate_csv():
    try:
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        service = ImportService(current_app.db)
        
        all_results = []
        total_rows = 0
        all_errors = []
        all_warnings = []
        all_valid = True
        
        for file in files:
            if file.filename == '':
                continue
                
            if not file.filename.lower().endswith('.csv'):
                all_errors.append(f"File {file.filename}: Invalid file type. Only CSV files allowed")
                all_valid = False
                continue
            
            try:
                validation = service.validate_csv(file)
                total_rows += validation['rows']
                
                if not validation['valid']:
                    all_valid = False
                
                # Prefix errors and warnings with filename
                for error in validation['errors']:
                    all_errors.append(f"File {file.filename} - {error}")
                for warning in validation['warnings']:
                    all_warnings.append(f"File {file.filename} - {warning}")
                    
                all_results.append({
                    'filename': file.filename,
                    'valid': validation['valid'],
                    'rows': validation['rows']
                })
            except Exception as e:
                all_errors.append(f"File {file.filename}: {str(e)}")
                all_valid = False
        
        return jsonify({
            'valid': all_valid,
            'total_rows': total_rows,
            'file_results': all_results,
            'errors': all_errors,
            'warnings': all_warnings
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/reset-headers', methods=['POST'])
def reset_csv_headers():
    try:
        # Remove the stored CSV header schema baseline
        current_app.db.execute("DELETE FROM app_config WHERE key = ?", ('import_csv_headers',))
        return jsonify({'message': 'CSV header baseline has been reset'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
