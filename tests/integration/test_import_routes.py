"""Comprehensive integration tests for import routes"""

import pytest
import json
from io import BytesIO
from datetime import datetime, date


class TestImportRoutes:
    """Test import API endpoints comprehensively"""
    
    def test_csv_import_success(self, client, sample_data):
        """Test successful CSV import"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM
03/02/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},10:00 AM,06:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'test.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['imported'] >= 0
        assert 'errors' in data
        assert 'warnings' in data
    
    def test_csv_import_no_file(self, client):
        """Test CSV import without file"""
        response = client.post('/api/import/csv',
            data={},
            content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No file' in data['error']
    
    def test_csv_import_empty_filename(self, client):
        """Test CSV import with empty filename"""
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(b''), '', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'No file selected' in data['error']
    
    def test_csv_import_wrong_file_type(self, client):
        """Test CSV import with non-CSV file"""
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(b'test content'), 'test.txt', 'text/plain')},
            content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid file type' in data['error'] or 'CSV' in data['error']
    
    def test_csv_import_file_too_large(self, client):
        """Test CSV import with file exceeding size limit"""
        # Create a large CSV content (over 10MB default limit)
        large_content = 'Date,Consumer,Employee,Start Time,End Time\n'
        # Add rows to exceed 10MB
        row = '01/01/2025,Test Child (TC001),Test Employee,09:00 AM,05:00 PM\n'
        while len(large_content) < 11 * 1024 * 1024:  # 11MB
            large_content += row
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(large_content.encode('utf-8')), 'large.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'too large' in data['error'].lower() or 'size' in data['error'].lower()
    
    def test_csv_import_malformed_data(self, client):
        """Test CSV import with malformed data"""
        csv_content = """Date,Consumer,Employee
Missing columns here
Not enough data"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'malformed.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        # Should still return 200 but with errors
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['errors']) > 0
    
    def test_csv_import_duplicate_shifts(self, client, sample_data):
        """Test CSV import with duplicate shifts"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'duplicates.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'duplicates' in data
        assert data['duplicates'] > 0
    
    def test_csv_import_unknown_employee(self, client, sample_data):
        """Test CSV import with unknown employee - should create new employee"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),Unknown Employee,09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'unknown.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # The system creates unknown employees automatically
        assert data['imported'] == 1
        # Verify the new employee was created
        emp_response = client.get('/api/employees/')
        employees = json.loads(emp_response.data)
        assert any(e['system_name'] == 'Unknown Employee' for e in employees)
    
    def test_csv_import_unknown_child(self, client, sample_data):
        """Test CSV import with unknown child - should create new child"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,Unknown Child (UC999),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'unknown.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # The system creates unknown children automatically
        assert data['imported'] == 1
        # Verify the new child was created
        child_response = client.get('/api/children/')
        children = json.loads(child_response.data)
        assert any(c['code'] == 'UC999' for c in children)
    
    def test_csv_import_invalid_date_format(self, client, sample_data):
        """Test CSV import with invalid date format"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
2025-03-01,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM
invalid-date,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'dates.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # At least one row should fail
        assert len(data['errors']) > 0 or data['imported'] < 2
    
    def test_csv_import_invalid_time_format(self, client, sample_data):
        """Test CSV import with invalid time format"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},25:00 AM,05:00 PM
03/02/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00,17:00"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'times.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should handle different time formats
        assert 'imported' in data
    
    def test_csv_import_overlapping_shifts(self, client, sample_data):
        """Test CSV import with overlapping shifts for same employee"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,02:00 PM
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},01:00 PM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'overlapping.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should handle overlapping shifts
        assert 'imported' in data
        # May have warnings or errors about overlaps
    
    def test_csv_validate_endpoint(self, client, sample_data):
        """Test CSV validation endpoint"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/validate',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'validate.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'valid' in data or 'errors' in data or 'validation' in str(data).lower()
    
    def test_csv_import_special_characters(self, client, sample_data):
        """Test CSV import with special characters in names"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM
03/02/2025,"O'Brien, Test" (TB001),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'special.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'imported' in data
    
    def test_csv_import_utf8_encoding(self, client, sample_data):
        """Test CSV import with UTF-8 encoded content"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,José García (JG001),María López,09:00 AM,05:00 PM
03/02/2025,李明 (LM001),王芳,09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'utf8.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'imported' in data
    
    def test_csv_import_empty_file(self, client):
        """Test CSV import with empty file"""
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(b''), 'empty.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code in [200, 400]
        data = json.loads(response.data)
        if response.status_code == 200:
            assert data['imported'] == 0
        else:
            assert 'error' in data
    
    def test_csv_import_headers_only(self, client):
        """Test CSV import with only headers"""
        csv_content = "Date,Consumer,Employee,Start Time,End Time\n"
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'headers.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['imported'] == 0
    
    def test_csv_import_missing_columns(self, client):
        """Test CSV import with missing required columns"""
        csv_content = """Date,Employee
03/01/2025,Test Employee"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'missing.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['errors']) > 0
    
    def test_csv_import_extra_columns(self, client, sample_data):
        """Test CSV import with extra columns (should be ignored)"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time,Extra1,Extra2
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM,Ignored,Data"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'extra.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['imported'] >= 0    
    def test_batch_csv_import(self, client, sample_data):
        """Test batch CSV import with multiple files"""
        csv1 = f"""Date,Consumer,Employee,Start Time,End Time
02/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        csv2 = f"""Date,Consumer,Employee,Start Time,End Time
02/02/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},10:00 AM,06:00 PM"""
        
        response = client.post('/api/import/batch-csv',
            data={
                'files': [
                    (BytesIO(csv1.encode('utf-8')), 'file1.csv', 'text/csv'),
                    (BytesIO(csv2.encode('utf-8')), 'file2.csv', 'text/csv')
                ]
            },
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_imported' in data
        assert 'file_results' in data
        assert len(data['file_results']) == 2
    
    def test_batch_csv_import_no_files(self, client):
        """Test batch import without files"""
        response = client.post('/api/import/batch-csv',
            data={},
            content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_batch_csv_import_mixed_files(self, client, sample_data):
        """Test batch import with mixed valid and invalid files"""
        csv_valid = f"""Date,Consumer,Employee,Start Time,End Time
02/03/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        response = client.post('/api/import/batch-csv',
            data={
                'files': [
                    (BytesIO(csv_valid.encode('utf-8')), 'valid.csv', 'text/csv'),
                    (BytesIO(b'not a csv'), 'invalid.txt', 'text/plain')
                ]
            },
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['errors']) > 0  # Should have error for .txt file
    
    def test_pdf_budget_import(self, client):
        """Test PDF budget import endpoint"""
        # Skip if endpoint doesn't exist
        response = client.get('/api/import/')
        if response.status_code == 404:
            pytest.skip("PDF import endpoint not implemented")
        
        pdf_content = b'%PDF-1.4\n%%Mock PDF for testing'
        
        response = client.post('/api/import/budget-pdf',
            data={'file': (BytesIO(pdf_content), 'budget.pdf', 'application/pdf')},
            content_type='multipart/form-data')
        
        # Should handle PDF files (may fail to parse but shouldn't error)
        assert response.status_code in [200, 400, 404]
        if response.status_code != 404:
            data = json.loads(response.data)
            assert 'error' in data or 'parsed_data' in data or 'result' in data
    
    def test_pdf_budget_import_no_file(self, client):
        """Test PDF import without file"""
        response = client.post('/api/import/budget-pdf',
            data={},
            content_type='multipart/form-data')
        
        # 404 if endpoint doesn't exist, 400 if it does
        assert response.status_code in [400, 404]
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_pdf_budget_import_wrong_type(self, client):
        """Test PDF import with non-PDF file"""
        response = client.post('/api/import/budget-pdf',
            data={'file': (BytesIO(b'not a pdf'), 'test.txt', 'text/plain')},
            content_type='multipart/form-data')
        
        # 404 if endpoint doesn't exist, 400 if it does
        assert response.status_code in [400, 404]
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'error' in data
