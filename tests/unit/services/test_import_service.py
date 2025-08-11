"""Unit tests for ImportService"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO
import csv
from services.import_service import ImportService


class TestImportService:
    """Test suite for ImportService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def mock_services(self):
        """Create mock service instances"""
        return {
            'employee': Mock(),
            'child': Mock(),
            'shift': Mock()
        }
    
    @pytest.fixture
    def service(self, mock_db, mock_services):
        """Create an ImportService instance with mock dependencies"""
        service = ImportService(mock_db)
        service.employee_service = mock_services['employee']
        service.child_service = mock_services['child']
        service.shift_service = mock_services['shift']
        return service
    
    @pytest.fixture
    def valid_csv_content(self):
        """Generate valid CSV content for testing"""
        return """Date,Consumer,Employee,Start Time,End Time,Service Code,Status
01/15/2025,Jane Smith (JS123),John Doe (JD456),Start: 9:00 AM,End: 5:00 PM,RESPITE,Approved
01/16/2025,Bob Jones,Mary Johnson,Start: 10:00 AM,End: 2:00 PM,PERSONAL,Approved"""
    
    @pytest.fixture
    def invalid_csv_content(self):
        """Generate invalid CSV content for testing"""
        return """Date,Consumer,Employee
01/15/2025,Jane Smith,John Doe"""
    
    @pytest.fixture
    def csv_file(self, valid_csv_content):
        """Create a mock CSV file object"""
        file = BytesIO(valid_csv_content.encode('utf-8'))
        file.seek(0)
        return file
    
    # Test parse_csv_row
    def test_parse_csv_row_with_codes(self, service):
        """Test parsing CSV row with employee and child codes"""
        row = {
            'Date': '01/15/2025',
            'Consumer': 'Jane Smith (JS123)',
            'Employee': 'John Doe (JD456)',
            'Start Time': 'Start: 9:00 AM',
            'End Time': 'End: 5:00 PM',
            'Service Code': 'RESPITE',
            'Status': 'Approved'
        }
        
        result = service.parse_csv_row(row)
        
        assert result['date'] == '2025-01-15'
        assert result['child_name'] == 'Jane Smith'
        assert result['child_code'] == 'JS123'
        assert result['employee_name'] == 'John Doe'
        assert result['employee_code'] == 'JD456'
        assert result['start_time'] == '09:00:00'
        assert result['end_time'] == '17:00:00'
        assert result['service_code'] == 'RESPITE'
        assert result['status'] == 'Approved'
    
    def test_parse_csv_row_without_codes(self, service):
        """Test parsing CSV row without codes"""
        row = {
            'Date': '01/15/2025',
            'Consumer': 'Jane Smith',
            'Employee': 'John Doe',
            'Start Time': '9:00 AM',
            'End Time': '5:00 PM',
            'Service Code': 'RESPITE',
            'Status': 'Approved'
        }
        
        result = service.parse_csv_row(row)
        
        assert result['child_name'] == 'Jane Smith'
        assert result['child_code'] is None
        assert result['employee_name'] == 'John Doe'
        assert result['employee_code'] is None
    
    def test_parse_csv_row_midnight_end_time(self, service):
        """Test parsing CSV row with midnight end time"""
        row = {
            'Date': '01/15/2025',
            'Consumer': 'Jane Smith',
            'Employee': 'John Doe',
            'Start Time': '10:00 PM',
            'End Time': '12:00 AM',
            'Service Code': 'NIGHT',
            'Status': 'Approved'
        }
        
        result = service.parse_csv_row(row)
        
        assert result['start_time'] == '22:00:00'
        assert result['end_time'] == '23:59:59'  # Midnight converted to end of day
    
    def test_parse_csv_row_various_time_formats(self, service):
        """Test parsing various time format variations"""
        test_cases = [
            ('Start: 9:00 AM', 'End: 5:00 PM', '09:00:00', '17:00:00'),
            ('9:00 AM', '5:00 PM', '09:00:00', '17:00:00'),
            ('Start: 12:30 PM', 'End: 11:45 PM', '12:30:00', '23:45:00'),
        ]
        
        for start_input, end_input, expected_start, expected_end in test_cases:
            row = {
                'Date': '01/15/2025',
                'Consumer': 'Test',
                'Employee': 'Test',
                'Start Time': start_input,
                'End Time': end_input
            }
            
            result = service.parse_csv_row(row)
            assert result['start_time'] == expected_start
            assert result['end_time'] == expected_end
    
    # Test validate_csv
    def test_validate_csv_valid_file(self, service, csv_file):
        """Test validating a valid CSV file"""
        result = service.validate_csv(csv_file)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['rows'] == 2
        # Should have warnings about missing codes
        assert len(result['warnings']) > 0
    
    def test_validate_csv_missing_columns(self, service, invalid_csv_content):
        """Test validating CSV with missing required columns"""
        file = BytesIO(invalid_csv_content.encode('utf-8'))
        
        result = service.validate_csv(file)
        
        assert result['valid'] is False
        assert 'Missing required columns' in result['errors'][0]
        assert result['rows'] == 0
    
    def test_validate_csv_invalid_date_format(self, service):
        """Test validating CSV with invalid date format"""
        content = """Date,Consumer,Employee,Start Time,End Time
invalid-date,Jane Smith,John Doe,9:00 AM,5:00 PM"""
        file = BytesIO(content.encode('utf-8'))
        
        result = service.validate_csv(file)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'Row 1' in result['errors'][0]
    
    def test_validate_csv_warnings_for_missing_codes(self, service):
        """Test that warnings are generated for missing codes"""
        content = """Date,Consumer,Employee,Start Time,End Time
01/15/2025,Jane Smith,John Doe,9:00 AM,5:00 PM"""
        file = BytesIO(content.encode('utf-8'))
        
        result = service.validate_csv(file)
        
        assert result['valid'] is True
        assert len(result['warnings']) == 2  # One for employee, one for child
        assert 'No code found' in result['warnings'][0]
    
    def test_validate_csv_exception_handling(self, service):
        """Test validation handles exceptions gracefully"""
        file = Mock()
        file.read.side_effect = Exception("Read error")
        
        result = service.validate_csv(file)
        
        assert result['valid'] is False
        assert 'Failed to parse CSV' in result['errors'][0]
    
    # Test import_csv
    def test_import_csv_new_entities(self, service, mock_services, mock_db, csv_file):
        """Test importing CSV creates new employees and children"""
        mock_services['employee'].get_by_system_name.return_value = None
        mock_services['employee'].create.return_value = 1
        mock_services['child'].get_by_code.return_value = None
        mock_services['child'].create.return_value = 1
        mock_services['shift'].validate_shift.return_value = []
        mock_services['shift'].create.return_value = 1
        mock_db.fetchone.return_value = None  # No existing shifts
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 2
        assert result['duplicates'] == 0
        assert result['replaced'] == 0
        assert len(result['errors']) == 0
        
        # Verify entities were created
        assert mock_services['employee'].create.call_count == 2
        assert mock_services['child'].create.call_count == 2
        assert mock_services['shift'].create.call_count == 2
    
    def test_import_csv_existing_entities(self, service, mock_services, mock_db, csv_file):
        """Test importing CSV with existing employees and children"""
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        mock_services['shift'].validate_shift.return_value = []
        mock_services['shift'].create.return_value = 1
        mock_db.fetchone.return_value = None  # No existing shifts
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 2
        assert result['duplicates'] == 0
        
        # Verify entities were not created (already exist)
        mock_services['employee'].create.assert_not_called()
        mock_services['child'].create.assert_not_called()
    
    def test_import_csv_duplicate_shifts(self, service, mock_services, mock_db, csv_file):
        """Test importing CSV with duplicate shifts (already imported)"""
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        # Existing imported shift
        mock_db.fetchone.return_value = {'id': 1, 'is_imported': 1}
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 0
        assert result['duplicates'] == 2
        assert result['replaced'] == 0
        
        # Shifts should not be created (duplicates)
        mock_services['shift'].create.assert_not_called()
    
    def test_import_csv_replace_manual_shifts(self, service, mock_services, mock_db, csv_file):
        """Test that imported shifts replace manual shifts"""
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        mock_services['shift'].validate_shift.return_value = []
        mock_services['shift'].create.return_value = 1
        # Existing manual shift (not imported)
        mock_db.fetchone.return_value = {'id': 1, 'is_imported': 0}
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 2
        assert result['duplicates'] == 0
        assert result['replaced'] == 2
        
        # Manual shifts should be deleted
        assert mock_services['shift'].delete.call_count == 2
        # New imported shifts should be created
        assert mock_services['shift'].create.call_count == 2
    
    def test_import_csv_validation_warnings(self, service, mock_services, mock_db, csv_file):
        """Test that validation warnings are included in import results"""
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        mock_services['shift'].validate_shift.return_value = ['Overlapping shift detected']
        mock_services['shift'].create.return_value = 1
        mock_db.fetchone.return_value = None
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 2
        assert len(result['warnings']) == 2  # One warning per row
        assert 'Overlapping shift detected' in result['warnings'][0]
    
    def test_import_csv_validation_errors(self, service, mock_services, mock_db):
        """Test that validation errors prevent shift creation"""
        content = """Date,Consumer,Employee,Start Time,End Time
01/15/2025,Jane Smith,John Doe,5:00 PM,9:00 AM"""  # Invalid time range
        file = BytesIO(content.encode('utf-8'))
        
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        mock_services['shift'].validate_shift.side_effect = ValueError("End time before start time")
        mock_db.fetchone.return_value = None
        
        result = service.import_csv(file)
        
        assert result['imported'] == 0
        assert len(result['errors']) == 1
        assert 'End time before start time' in result['errors'][0]
    
    def test_import_csv_exception_handling(self, service, mock_services, mock_db, csv_file):
        """Test that exceptions during import are handled gracefully"""
        mock_services['employee'].get_by_system_name.side_effect = Exception("Database error")
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 0
        assert len(result['errors']) == 2  # One error per row
        assert 'Database error' in result['errors'][0]
    
    def test_import_csv_with_service_codes(self, service, mock_services, mock_db, csv_file):
        """Test that service codes are properly imported"""
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        mock_services['child'].get_by_code.return_value = {'id': 1}
        mock_services['shift'].validate_shift.return_value = []
        mock_db.fetchone.return_value = None
        
        # Capture the create calls
        create_calls = []
        mock_services['shift'].create.side_effect = lambda **kwargs: create_calls.append(kwargs) or 1
        
        result = service.import_csv(csv_file)
        
        assert result['imported'] == 2
        # Verify service codes were passed
        assert create_calls[0]['service_code'] == 'RESPITE'
        assert create_calls[1]['service_code'] == 'PERSONAL'
        assert all(call['is_imported'] is True for call in create_calls)
    
    def test_import_csv_child_lookup_fallback(self, service, mock_services, mock_db):
        """Test child lookup falls back to name if code not found"""
        content = """Date,Consumer,Employee,Start Time,End Time
01/15/2025,Jane Smith,John Doe,9:00 AM,5:00 PM"""
        file = BytesIO(content.encode('utf-8'))
        
        mock_services['employee'].get_by_system_name.return_value = {'id': 1}
        # First call returns None (code lookup), second returns None (name lookup)
        mock_services['child'].get_by_code.side_effect = [None, None]
        mock_services['child'].create.return_value = 1
        mock_services['shift'].validate_shift.return_value = []
        mock_services['shift'].create.return_value = 1
        mock_db.fetchone.return_value = None
        
        result = service.import_csv(file)
        
        assert result['imported'] == 1
        # Verify child was created with name as code
        mock_services['child'].create.assert_called_once_with(
            name='Jane Smith',
            code='Jane Smith'
        )


class TestImportServiceIntegration:
    """Integration tests for ImportService with real database"""
    
    def test_import_csv_end_to_end(self, test_db, sample_data):
        """Test complete CSV import workflow"""
        service = ImportService(test_db)
        
        # Create CSV content with known data
        content = f"""Date,Consumer,Employee,Start Time,End Time,Service Code
01/20/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},9:00 AM,5:00 PM,TEST"""
        file = BytesIO(content.encode('utf-8'))
        
        # First import
        result = service.import_csv(file)
        
        assert result['imported'] == 1
        assert result['duplicates'] == 0
        assert result['replaced'] == 0
        
        # Verify shift was created
        shifts = test_db.fetchall(
            "SELECT * FROM shifts WHERE date = ?",
            ('2025-01-20',)
        )
        assert len(shifts) == 1
        assert shifts[0]['is_imported'] == 1
        
        # Second import of same data should be duplicate
        file.seek(0)
        result = service.import_csv(file)
        
        assert result['imported'] == 0
        assert result['duplicates'] == 1
    
    def test_import_replaces_manual_shifts(self, test_db, sample_data):
        """Test that imported shifts replace manual ones"""
        service = ImportService(test_db)
        shift_service = ShiftService(test_db)
        
        # Create a manual shift
        manual_shift_id = shift_service.create(
            employee_id=sample_data['employee'].id,
            child_id=sample_data['child'].id,
            date='2025-01-20',
            start_time='09:00:00',
            end_time='17:00:00',
            is_imported=False
        )
        
        # Import CSV with same shift
        content = f"""Date,Consumer,Employee,Start Time,End Time
01/20/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},9:00 AM,5:00 PM"""
        file = BytesIO(content.encode('utf-8'))
        
        result = service.import_csv(file)
        
        assert result['imported'] == 1
        assert result['replaced'] == 1
        
        # Verify manual shift was deleted
        manual_shift = test_db.fetchone(
            "SELECT * FROM shifts WHERE id = ?",
            (manual_shift_id,)
        )
        assert manual_shift is None
        
        # Verify imported shift exists
        imported_shifts = test_db.fetchall(
            "SELECT * FROM shifts WHERE date = ? AND is_imported = 1",
            ('2025-01-20',)
        )
        assert len(imported_shifts) == 1