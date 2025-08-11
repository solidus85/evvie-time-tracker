"""
Unit tests for EmployeeService
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from services.employee_service import EmployeeService


class TestEmployeeService:
    """Test suite for EmployeeService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create an EmployeeService instance with mock database"""
        return EmployeeService(mock_db)
    
    # Test get_all method
    def test_get_all_returns_all_employees(self, service, mock_db):
        """Test getting all employees"""
        expected_employees = [
            {'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1},
            {'id': 2, 'friendly_name': 'Jane Smith', 'system_name': 'jsmith', 'active': 1},
            {'id': 3, 'friendly_name': 'Bob Wilson', 'system_name': 'bwilson', 'active': 0}
        ]
        mock_db.fetchall.return_value = expected_employees
        
        result = service.get_all()
        
        assert result == expected_employees
        mock_db.fetchall.assert_called_once_with(
            "SELECT * FROM employees ORDER BY friendly_name"
        )
    
    def test_get_all_active_only_filters_inactive(self, service, mock_db):
        """Test getting only active employees"""
        expected_employees = [
            {'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1},
            {'id': 2, 'friendly_name': 'Jane Smith', 'system_name': 'jsmith', 'active': 1}
        ]
        mock_db.fetchall.return_value = expected_employees
        
        result = service.get_all(active_only=True)
        
        assert result == expected_employees
        mock_db.fetchall.assert_called_once_with(
            "SELECT * FROM employees WHERE active = 1 ORDER BY friendly_name"
        )
    
    def test_get_all_returns_empty_list_when_no_employees(self, service, mock_db):
        """Test get_all returns empty list when no employees exist"""
        mock_db.fetchall.return_value = []
        
        result = service.get_all()
        
        assert result == []
        mock_db.fetchall.assert_called_once()
    
    # Test get_by_id method
    def test_get_by_id_returns_employee(self, service, mock_db):
        """Test getting employee by ID"""
        expected_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = expected_employee
        
        result = service.get_by_id(1)
        
        assert result == expected_employee
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE id = ?",
            (1,)
        )
    
    def test_get_by_id_returns_none_for_invalid_id(self, service, mock_db):
        """Test get_by_id returns None for non-existent ID"""
        mock_db.fetchone.return_value = None
        
        result = service.get_by_id(999)
        
        assert result is None
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE id = ?",
            (999,)
        )
    
    # Test get_by_system_name method
    def test_get_by_system_name_returns_employee(self, service, mock_db):
        """Test getting employee by system name"""
        expected_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = expected_employee
        
        result = service.get_by_system_name('jdoe')
        
        assert result == expected_employee
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE system_name = ?",
            ('jdoe',)
        )
    
    def test_get_by_system_name_returns_none_for_invalid_name(self, service, mock_db):
        """Test get_by_system_name returns None for non-existent name"""
        mock_db.fetchone.return_value = None
        
        result = service.get_by_system_name('nonexistent')
        
        assert result is None
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE system_name = ?",
            ('nonexistent',)
        )
    
    # Test create method
    def test_create_employee_success(self, service, mock_db):
        """Test successfully creating a new employee"""
        mock_db.fetchone.return_value = None  # No existing employee
        mock_db.insert.return_value = 42  # New employee ID
        
        result = service.create('John Doe', 'jdoe', active=True)
        
        assert result == 42
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE system_name = ?",
            ('jdoe',)
        )
        mock_db.insert.assert_called_once_with(
            "INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)",
            ('John Doe', 'jdoe', True)
        )
    
    def test_create_employee_with_duplicate_system_name_raises_error(self, service, mock_db):
        """Test creating employee with duplicate system name raises ValueError"""
        existing_employee = {
            'id': 1, 'friendly_name': 'Existing User', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        with pytest.raises(ValueError, match="Employee with system name 'jdoe' already exists"):
            service.create('John Doe', 'jdoe')
        
        mock_db.fetchone.assert_called_once()
        mock_db.insert.assert_not_called()
    
    def test_create_employee_defaults_to_active(self, service, mock_db):
        """Test create employee defaults to active=True"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        result = service.create('John Doe', 'jdoe')
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            "INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)",
            ('John Doe', 'jdoe', True)
        )
    
    def test_create_inactive_employee(self, service, mock_db):
        """Test creating an inactive employee"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        result = service.create('John Doe', 'jdoe', active=False)
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            "INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)",
            ('John Doe', 'jdoe', False)
        )
    
    # Test update method
    def test_update_employee_friendly_name(self, service, mock_db):
        """Test updating employee's friendly name"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.update(1, {'friendly_name': 'John Smith'})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET friendly_name = ? WHERE id = ?",
            ['John Smith', 1]
        )
    
    def test_update_employee_system_name(self, service, mock_db):
        """Test updating employee's system name"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_employee, None]  # First call returns employee, second returns None
        
        result = service.update(1, {'system_name': 'jsmith'})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET system_name = ? WHERE id = ?",
            ['jsmith', 1]
        )
    
    def test_update_employee_system_name_duplicate_raises_error(self, service, mock_db):
        """Test updating to duplicate system name raises ValueError"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        another_employee = {
            'id': 2, 'friendly_name': 'Jane Smith', 'system_name': 'jsmith', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_employee, another_employee]
        
        with pytest.raises(ValueError, match="Employee with system name 'jsmith' already exists"):
            service.update(1, {'system_name': 'jsmith'})
        
        mock_db.execute.assert_not_called()
    
    def test_update_employee_active_status(self, service, mock_db):
        """Test updating employee's active status"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.update(1, {'active': 0})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET active = ? WHERE id = ?",
            [0, 1]
        )
    
    def test_update_multiple_fields(self, service, mock_db):
        """Test updating multiple fields at once"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_employee, None]
        
        result = service.update(1, {
            'friendly_name': 'John Smith',
            'system_name': 'jsmith',
            'active': 0
        })
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET friendly_name = ?, system_name = ?, active = ? WHERE id = ?",
            ['John Smith', 'jsmith', 0, 1]
        )
    
    def test_update_nonexistent_employee_returns_false(self, service, mock_db):
        """Test updating non-existent employee returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.update(999, {'friendly_name': 'New Name'})
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_update_with_no_changes_returns_true(self, service, mock_db):
        """Test update with empty data returns True without DB call"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.update(1, {})
        
        assert result is True
        mock_db.execute.assert_not_called()
    
    def test_update_same_system_name_succeeds(self, service, mock_db):
        """Test updating with same system name succeeds"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.update(1, {'system_name': 'jdoe', 'friendly_name': 'John Smith'})
        
        assert result is True
        # Should update both fields even though system_name is unchanged
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET friendly_name = ?, system_name = ? WHERE id = ?",
            ['John Smith', 'jdoe', 1]
        )
    
    # Test deactivate method
    def test_deactivate_employee_success(self, service, mock_db):
        """Test successfully deactivating an employee"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 1
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.deactivate(1)
        
        assert result is True
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE id = ?",
            (1,)
        )
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_already_inactive_employee(self, service, mock_db):
        """Test deactivating already inactive employee still succeeds"""
        existing_employee = {
            'id': 1, 'friendly_name': 'John Doe', 'system_name': 'jdoe', 'active': 0
        }
        mock_db.fetchone.return_value = existing_employee
        
        result = service.deactivate(1)
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE employees SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_nonexistent_employee_returns_false(self, service, mock_db):
        """Test deactivating non-existent employee returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.deactivate(999)
        
        assert result is False
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM employees WHERE id = ?",
            (999,)
        )
        mock_db.execute.assert_not_called()
    
    # Edge cases and error handling
    def test_handle_database_errors_gracefully(self, service, mock_db):
        """Test that database errors are propagated correctly"""
        mock_db.fetchall.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception, match="Database connection error"):
            service.get_all()
    
    def test_create_with_empty_strings_raises_database_error(self, service, mock_db):
        """Test creating employee with empty strings"""
        mock_db.fetchone.return_value = None
        mock_db.insert.side_effect = Exception("NOT NULL constraint failed")
        
        with pytest.raises(Exception, match="NOT NULL constraint failed"):
            service.create('', '')
    
    def test_create_with_none_values_raises_database_error(self, service, mock_db):
        """Test creating employee with None values"""
        mock_db.fetchone.return_value = None
        mock_db.insert.side_effect = Exception("NOT NULL constraint failed")
        
        with pytest.raises(Exception, match="NOT NULL constraint failed"):
            service.create(None, None)