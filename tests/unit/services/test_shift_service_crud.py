"""
Unit tests for ShiftService CRUD operations
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, time, datetime
from services.shift_service import ShiftService


class TestShiftServiceCRUD:
    """Test suite for ShiftService CRUD operations"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def mock_payroll_service(self):
        """Create a mock PayrollService"""
        return Mock()
    
    @pytest.fixture
    def mock_config_service(self):
        """Create a mock ConfigService"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db, mock_payroll_service, mock_config_service):
        """Create a ShiftService instance with mocked dependencies"""
        with patch('services.shift_service.PayrollService', return_value=mock_payroll_service):
            with patch('services.shift_service.ConfigService', return_value=mock_config_service):
                return ShiftService(mock_db)
    
    # Test get_shifts method
    def test_get_shifts_no_filters(self, service, mock_db):
        """Test getting all shifts without filters"""
        expected_shifts = [
            {'id': 1, 'employee_id': 1, 'child_id': 1, 'date': '2024-01-08', 
             'start_time': '09:00:00', 'end_time': '17:00:00', 
             'employee_name': 'John Doe', 'child_name': 'Alice Smith'},
            {'id': 2, 'employee_id': 2, 'child_id': 2, 'date': '2024-01-08', 
             'start_time': '10:00:00', 'end_time': '18:00:00',
             'employee_name': 'Jane Smith', 'child_name': 'Bob Jones'}
        ]
        mock_db.fetchall.return_value = expected_shifts
        
        result = service.get_shifts()
        
        assert result == expected_shifts
        expected_query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
         ORDER BY s.date DESC, s.start_time DESC"""
        mock_db.fetchall.assert_called_once_with(expected_query, [])
    
    def test_get_shifts_with_date_filters(self, service, mock_db):
        """Test getting shifts with date range filters"""
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        mock_db.fetchall.return_value = []
        
        service.get_shifts(start_date=start_date, end_date=end_date)
        
        expected_query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
         AND s.date >= ? AND s.date <= ? ORDER BY s.date DESC, s.start_time DESC"""
        mock_db.fetchall.assert_called_once_with(expected_query, [start_date, end_date])
    
    def test_get_shifts_with_employee_filter(self, service, mock_db):
        """Test getting shifts for specific employee"""
        employee_id = 5
        mock_db.fetchall.return_value = []
        
        service.get_shifts(employee_id=employee_id)
        
        expected_query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
         AND s.employee_id = ? ORDER BY s.date DESC, s.start_time DESC"""
        mock_db.fetchall.assert_called_once_with(expected_query, [employee_id])
    
    def test_get_shifts_with_child_filter(self, service, mock_db):
        """Test getting shifts for specific child"""
        child_id = 3
        mock_db.fetchall.return_value = []
        
        service.get_shifts(child_id=child_id)
        
        expected_query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
         AND s.child_id = ? ORDER BY s.date DESC, s.start_time DESC"""
        mock_db.fetchall.assert_called_once_with(expected_query, [child_id])
    
    def test_get_shifts_with_all_filters(self, service, mock_db):
        """Test getting shifts with all filters applied"""
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        employee_id = 2
        child_id = 3
        mock_db.fetchall.return_value = []
        
        service.get_shifts(
            start_date=start_date,
            end_date=end_date,
            employee_id=employee_id,
            child_id=child_id
        )
        
        expected_query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
         AND s.date >= ? AND s.date <= ? AND s.employee_id = ? AND s.child_id = ? ORDER BY s.date DESC, s.start_time DESC"""
        mock_db.fetchall.assert_called_once_with(
            expected_query, 
            [start_date, end_date, employee_id, child_id]
        )
    
    # Test get_by_id method
    def test_get_by_id_returns_shift(self, service, mock_db):
        """Test getting shift by ID"""
        expected_shift = {
            'id': 1, 'employee_id': 1, 'child_id': 1, 
            'date': '2024-01-08', 'start_time': '09:00:00', 'end_time': '17:00:00',
            'employee_name': 'John Doe', 'child_name': 'Alice Smith',
            'is_imported': 0, 'status': 'confirmed'
        }
        mock_db.fetchone.return_value = expected_shift
        
        result = service.get_by_id(1)
        
        assert result == expected_shift
        expected_query = """SELECT s.*, e.friendly_name as employee_name, c.name as child_name
               FROM shifts s
               JOIN employees e ON s.employee_id = e.id
               JOIN children c ON s.child_id = c.id
               WHERE s.id = ?"""
        mock_db.fetchone.assert_called_once_with(expected_query, (1,))
    
    def test_get_by_id_returns_none_for_invalid_id(self, service, mock_db):
        """Test get_by_id returns None for non-existent ID"""
        mock_db.fetchone.return_value = None
        
        result = service.get_by_id(999)
        
        assert result is None
        mock_db.fetchone.assert_called_once()
    
    # Test create method
    def test_create_shift_with_defaults(self, service, mock_db):
        """Test creating a shift with default values"""
        mock_db.insert.return_value = 42
        
        result = service.create(
            employee_id=1,
            child_id=2,
            date='2024-01-08',
            start_time='09:00:00',
            end_time='17:00:00'
        )
        
        assert result == 42
        mock_db.insert.assert_called_once_with(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, service_code, status, is_imported)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, 2, '2024-01-08', '09:00:00', '17:00:00', None, 'new', False)
        )
    
    def test_create_shift_with_all_parameters(self, service, mock_db):
        """Test creating a shift with all parameters specified"""
        mock_db.insert.return_value = 43
        
        result = service.create(
            employee_id=1,
            child_id=2,
            date='2024-01-08',
            start_time='09:00:00',
            end_time='17:00:00',
            service_code='THERAPY',
            status='confirmed',
            is_imported=True
        )
        
        assert result == 43
        mock_db.insert.assert_called_once_with(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, service_code, status, is_imported)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, 2, '2024-01-08', '09:00:00', '17:00:00', 'THERAPY', 'confirmed', True)
        )
    
    def test_create_shift_with_none_service_code(self, service, mock_db):
        """Test creating a shift with None service code"""
        mock_db.insert.return_value = 44
        
        result = service.create(
            employee_id=3,
            child_id=4,
            date='2024-01-09',
            start_time='10:00:00',
            end_time='14:00:00',
            service_code=None
        )
        
        assert result == 44
        mock_db.insert.assert_called_once()
        call_args = mock_db.insert.call_args[0]
        assert call_args[1][5] is None  # service_code should be None
    
    # Test update method
    def test_update_shift_success(self, service, mock_db):
        """Test successfully updating a manual shift"""
        existing_shift = {
            'id': 1, 'employee_id': 1, 'child_id': 2,
            'date': '2024-01-08', 'start_time': '09:00:00', 'end_time': '17:00:00',
            'is_imported': 0, 'status': 'new'
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.update(1, {
            'start_time': '08:00:00',
            'end_time': '16:00:00',
            'status': 'confirmed'
        })
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE shifts SET start_time = ?, end_time = ?, status = ? WHERE id = ?",
            ['08:00:00', '16:00:00', 'confirmed', 1]
        )
    
    def test_update_all_allowed_fields(self, service, mock_db):
        """Test updating all allowed fields"""
        existing_shift = {
            'id': 1, 'is_imported': 0
        }
        mock_db.fetchone.return_value = existing_shift
        
        update_data = {
            'employee_id': 2,
            'child_id': 3,
            'date': '2024-01-09',
            'start_time': '10:00:00',
            'end_time': '18:00:00',
            'service_code': 'THERAPY',
            'status': 'confirmed'
        }
        
        result = service.update(1, update_data)
        
        assert result is True
        expected_query = "UPDATE shifts SET employee_id = ?, child_id = ?, date = ?, start_time = ?, end_time = ?, service_code = ?, status = ? WHERE id = ?"
        expected_params = [2, 3, '2024-01-09', '10:00:00', '18:00:00', 'THERAPY', 'confirmed', 1]
        mock_db.execute.assert_called_once_with(expected_query, expected_params)
    
    def test_update_imported_shift_returns_false(self, service, mock_db):
        """Test updating an imported shift returns False"""
        existing_shift = {
            'id': 1, 'is_imported': 1
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.update(1, {'status': 'confirmed'})
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_update_nonexistent_shift_returns_false(self, service, mock_db):
        """Test updating non-existent shift returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.update(999, {'status': 'confirmed'})
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_update_with_no_changes_returns_true(self, service, mock_db):
        """Test update with empty data returns True without DB call"""
        existing_shift = {
            'id': 1, 'is_imported': 0
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.update(1, {})
        
        assert result is True
        mock_db.execute.assert_not_called()
    
    def test_update_ignores_invalid_fields(self, service, mock_db):
        """Test update ignores fields not in allowed list"""
        existing_shift = {
            'id': 1, 'is_imported': 0
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.update(1, {
            'status': 'confirmed',
            'is_imported': 1,  # Should be ignored
            'invalid_field': 'value'  # Should be ignored
        })
        
        assert result is True
        # Only status should be updated
        mock_db.execute.assert_called_once_with(
            "UPDATE shifts SET status = ? WHERE id = ?",
            ['confirmed', 1]
        )
    
    # Test delete method  
    def test_delete_shift_success(self, service, mock_db):
        """Test successfully deleting a manual shift"""
        existing_shift = {
            'id': 1, 'is_imported': 0
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.delete(1)
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "DELETE FROM shifts WHERE id = ?",
            (1,)
        )
    
    def test_delete_imported_shift_returns_false(self, service, mock_db):
        """Test deleting an imported shift returns False"""
        existing_shift = {
            'id': 1, 'is_imported': 1
        }
        mock_db.fetchone.return_value = existing_shift
        
        result = service.delete(1)
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_delete_nonexistent_shift_returns_false(self, service, mock_db):
        """Test deleting non-existent shift returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.delete(999)
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    # Edge cases and error handling
    def test_get_shifts_handles_empty_results(self, service, mock_db):
        """Test get_shifts handles empty result set"""
        mock_db.fetchall.return_value = []
        
        result = service.get_shifts()
        
        assert result == []
        mock_db.fetchall.assert_called_once()
    
    def test_create_propagates_database_errors(self, service, mock_db):
        """Test create propagates database errors"""
        mock_db.insert.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            service.create(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    def test_update_handles_database_errors(self, service, mock_db):
        """Test update handles database errors gracefully"""
        existing_shift = {'id': 1, 'is_imported': 0}
        mock_db.fetchone.return_value = existing_shift
        mock_db.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            service.update(1, {'status': 'confirmed'})