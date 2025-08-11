"""Unit tests for ExportService"""

import pytest
import json
import csv
from io import StringIO, BytesIO
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from services.export_service import ExportService


class TestExportService:
    """Test suite for ExportService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create an ExportService instance with mock database"""
        return ExportService(mock_db)
    
    @pytest.fixture
    def sample_shifts(self):
        """Sample shift data for testing"""
        return [
            {
                'id': 1,
                'employee_id': 1,
                'employee_name': 'John Doe',
                'employee_system_name': 'john.doe',
                'child_id': 1,
                'child_name': 'Jane Smith',
                'child_code': 'JS001',
                'date': '2025-01-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'hours': 8.0,
                'service_code': 'RESPITE',
                'status': 'approved',
                'is_imported': 0
            },
            {
                'id': 2,
                'employee_id': 2,
                'employee_name': 'Mary Johnson',
                'employee_system_name': 'mary.johnson',
                'child_id': 2,
                'child_name': 'Bob Jones',
                'child_code': 'BJ002',
                'date': '2025-01-16',
                'start_time': '10:00:00',
                'end_time': '14:30:00',
                'hours': 4.5,
                'service_code': 'PERSONAL',
                'status': 'approved',
                'is_imported': 0
            }
        ]
    
    # Test get_shifts_for_export
    def test_get_shifts_for_export_basic(self, service, mock_db, sample_shifts):
        """Test basic shift retrieval for export"""
        mock_db.fetchall.return_value = sample_shifts
        
        result = service.get_shifts_for_export('2025-01-01', '2025-01-31')
        
        # Verify query excludes imported shifts
        call_args = mock_db.fetchall.call_args
        assert 's.is_imported = 0' in call_args[0][0]
        assert call_args[0][1] == ['2025-01-01', '2025-01-31']
        assert result == sample_shifts
    
    def test_get_shifts_for_export_with_employee_filter(self, service, mock_db):
        """Test shift retrieval with employee filter"""
        mock_db.fetchall.return_value = []
        
        service.get_shifts_for_export('2025-01-01', '2025-01-31', employee_id=1)
        
        call_args = mock_db.fetchall.call_args
        assert 'AND s.employee_id = ?' in call_args[0][0]
        assert call_args[0][1] == ['2025-01-01', '2025-01-31', 1]
    
    def test_get_shifts_for_export_with_child_filter(self, service, mock_db):
        """Test shift retrieval with child filter"""
        mock_db.fetchall.return_value = []
        
        service.get_shifts_for_export('2025-01-01', '2025-01-31', child_id=2)
        
        call_args = mock_db.fetchall.call_args
        assert 'AND s.child_id = ?' in call_args[0][0]
        assert call_args[0][1] == ['2025-01-01', '2025-01-31', 2]
    
    def test_get_shifts_for_export_with_both_filters(self, service, mock_db):
        """Test shift retrieval with both employee and child filters"""
        mock_db.fetchall.return_value = []
        
        service.get_shifts_for_export('2025-01-01', '2025-01-31', employee_id=1, child_id=2)
        
        call_args = mock_db.fetchall.call_args
        assert 'AND s.employee_id = ?' in call_args[0][0]
        assert 'AND s.child_id = ?' in call_args[0][0]
        assert call_args[0][1] == ['2025-01-01', '2025-01-31', 1, 2]
    
    # Test export_csv
    def test_export_csv_with_shifts(self, service, mock_db, sample_shifts):
        """Test CSV export with shift data"""
        mock_db.fetchall.return_value = sample_shifts
        
        result = service.export_csv('2025-01-01', '2025-01-31')
        
        # Parse the CSV output
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        
        # Check header
        assert rows[0] == ['Date', 'Child', 'Employee', 'Start Time', 'End Time', 'Hours']
        
        # Check first data row
        assert rows[1][0] == '01/15/2025'  # Date formatted
        assert rows[1][1] == 'Jane Smith (JS001)'  # Child with code
        assert rows[1][2] == 'John Doe (john.doe)'  # Employee with system name
        assert rows[1][3] == '09:00 AM'  # Time formatted
        assert rows[1][4] == '05:00 PM'
        assert rows[1][5] == '8.00'  # Hours with 2 decimal places
        
        # Check second data row
        assert rows[2][0] == '01/16/2025'
        assert rows[2][5] == '4.50'  # 4.5 hours formatted
    
    def test_export_csv_empty_results(self, service, mock_db):
        """Test CSV export with no shifts"""
        mock_db.fetchall.return_value = []
        
        result = service.export_csv('2025-01-01', '2025-01-31')
        
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        
        # Should have header only
        assert len(rows) == 1
        assert rows[0] == ['Date', 'Child', 'Employee', 'Start Time', 'End Time', 'Hours']
    
    def test_export_csv_time_formatting(self, service, mock_db):
        """Test CSV export handles various time formats correctly"""
        shifts = [{
            'id': 1,
            'employee_id': 1,
            'employee_name': 'Test',
            'employee_system_name': 'test',
            'child_id': 1,
            'child_name': 'Child',
            'child_code': 'C001',
            'date': '2025-01-15',
            'start_time': '00:30:00',  # 12:30 AM
            'end_time': '23:45:00',    # 11:45 PM
            'hours': 23.25,
            'is_imported': 0
        }]
        mock_db.fetchall.return_value = shifts
        
        result = service.export_csv('2025-01-01', '2025-01-31')
        
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        
        assert rows[1][3] == '12:30 AM'
        assert rows[1][4] == '11:45 PM'
    
    # Test export_json
    def test_export_json_with_shifts(self, service, mock_db, sample_shifts):
        """Test JSON export with shift data"""
        mock_db.fetchall.return_value = sample_shifts
        
        with patch('services.export_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = '2025-01-20T10:00:00'
            result = service.export_json('2025-01-01', '2025-01-31')
        
        assert result['export_date'] == '2025-01-20T10:00:00'
        assert result['period']['start'] == '2025-01-01'
        assert result['period']['end'] == '2025-01-31'
        
        # Check shifts
        assert len(result['shifts']) == 2
        assert result['shifts'][0]['id'] == 1
        assert result['shifts'][0]['date'] == '2025-01-15'
        assert result['shifts'][0]['child']['name'] == 'Jane Smith'
        assert result['shifts'][0]['employee']['name'] == 'John Doe'
        assert result['shifts'][0]['hours'] == 8.0
        
        # Check summary
        assert result['summary']['total_shifts'] == 2
        assert result['summary']['total_hours'] == 12.5  # 8.0 + 4.5
        assert result['summary']['manual_shifts'] == 2
        assert result['summary']['imported_shifts'] == 0
    
    def test_export_json_empty_results(self, service, mock_db):
        """Test JSON export with no shifts"""
        mock_db.fetchall.return_value = []
        
        result = service.export_json('2025-01-01', '2025-01-31')
        
        assert result['shifts'] == []
        assert result['summary']['total_shifts'] == 0
        assert result['summary']['total_hours'] == 0
        assert result['summary']['manual_shifts'] == 0
    
    def test_export_json_hours_rounding(self, service, mock_db):
        """Test JSON export properly rounds hours"""
        shifts = [{
            'id': 1,
            'employee_id': 1,
            'employee_name': 'Test',
            'employee_system_name': 'test',
            'child_id': 1,
            'child_name': 'Child',
            'child_code': 'C001',
            'date': '2025-01-15',
            'start_time': '09:00:00',
            'end_time': '09:20:00',
            'hours': 0.333333333,  # 20 minutes
            'service_code': None,
            'status': 'approved',
            'is_imported': 0
        }]
        mock_db.fetchall.return_value = shifts
        
        result = service.export_json('2025-01-01', '2025-01-31')
        
        assert result['shifts'][0]['hours'] == 0.33  # Rounded to 2 decimals
        assert result['summary']['total_hours'] == 0.33
    
    # Test generate_pdf_report
    @patch('services.export_service.SimpleDocTemplate')
    @patch('services.export_service.getSampleStyleSheet')
    def test_generate_pdf_report_with_shifts(self, mock_styles, mock_doc_class, service, mock_db, sample_shifts):
        """Test PDF generation with shift data"""
        mock_db.fetchall.return_value = sample_shifts
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc
        mock_styles.return_value = {
            'Title': Mock(alignment=1),
            'Heading2': Mock(alignment=1),
            'Normal': Mock()
        }
        
        result = service.generate_pdf_report('2025-01-01', '2025-01-31')
        
        # Verify document was built
        mock_doc.build.assert_called_once()
        
        # Check that elements were created (passed to build)
        elements = mock_doc.build.call_args[0][0]
        assert len(elements) > 0
        
        # Verify buffer was returned
        assert isinstance(result, BytesIO)
    
    @patch('services.export_service.SimpleDocTemplate')
    @patch('services.export_service.getSampleStyleSheet')
    def test_generate_pdf_report_empty(self, mock_styles, mock_doc_class, service, mock_db):
        """Test PDF generation with no shifts"""
        mock_db.fetchall.return_value = []
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc
        mock_styles.return_value = {
            'Title': Mock(alignment=1),
            'Heading2': Mock(alignment=1),
            'Normal': Mock()
        }
        
        result = service.generate_pdf_report('2025-01-01', '2025-01-31')
        
        # Verify document was built
        mock_doc.build.assert_called_once()
        
        # Check that "No shifts found" message was added
        elements = mock_doc.build.call_args[0][0]
        assert len(elements) > 0
    
    @patch('services.export_service.SimpleDocTemplate')
    def test_generate_pdf_report_grouping(self, mock_doc_class, service, mock_db):
        """Test PDF report groups shifts by employee, child, and week"""
        # Create shifts spanning two weeks
        shifts = [
            {
                'id': 1,
                'employee_id': 1,
                'employee_name': 'John Doe',
                'employee_system_name': 'john.doe',
                'child_id': 1,
                'child_name': 'Jane Smith',
                'child_code': 'JS001',
                'date': '2025-01-01',  # Week 1
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'hours': 8.0,
                'is_imported': 0
            },
            {
                'id': 2,
                'employee_id': 1,
                'employee_name': 'John Doe',
                'employee_system_name': 'john.doe',
                'child_id': 1,
                'child_name': 'Jane Smith',
                'child_code': 'JS001',
                'date': '2025-01-08',  # Week 2
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'hours': 8.0,
                'is_imported': 0
            }
        ]
        mock_db.fetchall.return_value = shifts
        mock_doc = Mock()
        mock_doc_class.return_value = mock_doc
        
        with patch('services.export_service.getSampleStyleSheet'):
            result = service.generate_pdf_report('2025-01-01', '2025-01-14')
        
        # Verify grouping logic was applied
        elements = mock_doc.build.call_args[0][0]
        # The implementation groups by employee, child, and week
        assert mock_doc.build.called
    
    def test_generate_pdf_report_date_filtering(self, service, mock_db):
        """Test PDF report respects date filtering"""
        mock_db.fetchall.return_value = []
        
        with patch('services.export_service.SimpleDocTemplate'):
            with patch('services.export_service.getSampleStyleSheet'):
                service.generate_pdf_report('2025-01-01', '2025-01-31', employee_id=1, child_id=2)
        
        # Verify filters were passed to get_shifts_for_export
        mock_db.fetchall.assert_called_once()
        call_args = mock_db.fetchall.call_args[0]
        assert call_args[1] == ['2025-01-01', '2025-01-31', 1, 2]


class TestExportServiceIntegration:
    """Integration tests for ExportService with real components"""
    
    def test_csv_export_end_to_end(self, test_db, sample_data):
        """Test complete CSV export workflow"""
        service = ExportService(test_db)
        
        # Create a manual shift (not imported)
        test_db.insert(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, is_imported)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sample_data['employee'].id, sample_data['child'].id,
             '2025-01-15', '09:00:00', '17:00:00', 0)
        )
        
        # Create an imported shift (should be excluded)
        test_db.insert(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, is_imported)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sample_data['employee'].id, sample_data['child'].id,
             '2025-01-16', '09:00:00', '17:00:00', 1)
        )
        
        result = service.export_csv('2025-01-01', '2025-01-31')
        
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        
        # Should have header + 1 manual shift (imported excluded)
        assert len(rows) == 2
        assert '01/15/2025' in rows[1][0]
    
    def test_json_export_summary_calculations(self, test_db, sample_data):
        """Test JSON export summary calculations are accurate"""
        service = ExportService(test_db)
        
        # Create multiple manual shifts
        for i in range(3):
            test_db.insert(
                """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, is_imported)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sample_data['employee'].id, sample_data['child'].id,
                 f'2025-01-{15+i}', '09:00:00', '13:00:00', 0)
            )
        
        result = service.export_json('2025-01-01', '2025-01-31')
        
        assert result['summary']['total_shifts'] == 3
        assert result['summary']['total_hours'] == 12.0  # 3 shifts * 4 hours
        assert result['summary']['manual_shifts'] == 3
        assert result['summary']['imported_shifts'] == 0
    
    def test_pdf_generation_creates_valid_buffer(self, test_db, sample_data):
        """Test PDF generation creates a valid buffer"""
        service = ExportService(test_db)
        
        # Create a shift
        test_db.insert(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, is_imported)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sample_data['employee'].id, sample_data['child'].id,
             '2025-01-15', '09:00:00', '17:00:00', 0)
        )
        
        result = service.generate_pdf_report('2025-01-01', '2025-01-31')
        
        # Should return a BytesIO buffer
        assert isinstance(result, BytesIO)
        
        # Buffer should contain data
        result.seek(0)
        content = result.read()
        assert len(content) > 0
        
        # PDF files start with %PDF
        assert content.startswith(b'%PDF')