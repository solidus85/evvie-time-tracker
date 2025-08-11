"""
Unit tests for ChildService
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from services.child_service import ChildService


class TestChildService:
    """Test suite for ChildService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a ChildService instance with mock database"""
        return ChildService(mock_db)
    
    # Test get_all method
    def test_get_all_returns_all_children(self, service, mock_db):
        """Test getting all children"""
        expected_children = [
            {'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1},
            {'id': 2, 'name': 'Bob Jones', 'code': 'BJ002', 'active': 1},
            {'id': 3, 'name': 'Charlie Brown', 'code': 'CB003', 'active': 0}
        ]
        mock_db.fetchall.return_value = expected_children
        
        result = service.get_all()
        
        assert result == expected_children
        mock_db.fetchall.assert_called_once_with(
            "SELECT * FROM children ORDER BY name"
        )
    
    def test_get_all_active_only_filters_inactive(self, service, mock_db):
        """Test getting only active children"""
        expected_children = [
            {'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1},
            {'id': 2, 'name': 'Bob Jones', 'code': 'BJ002', 'active': 1}
        ]
        mock_db.fetchall.return_value = expected_children
        
        result = service.get_all(active_only=True)
        
        assert result == expected_children
        mock_db.fetchall.assert_called_once_with(
            "SELECT * FROM children WHERE active = 1 ORDER BY name"
        )
    
    def test_get_all_returns_empty_list_when_no_children(self, service, mock_db):
        """Test get_all returns empty list when no children exist"""
        mock_db.fetchall.return_value = []
        
        result = service.get_all()
        
        assert result == []
        mock_db.fetchall.assert_called_once()
    
    # Test get_by_id method
    def test_get_by_id_returns_child(self, service, mock_db):
        """Test getting child by ID"""
        expected_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = expected_child
        
        result = service.get_by_id(1)
        
        assert result == expected_child
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE id = ?",
            (1,)
        )
    
    def test_get_by_id_returns_none_for_invalid_id(self, service, mock_db):
        """Test get_by_id returns None for non-existent ID"""
        mock_db.fetchone.return_value = None
        
        result = service.get_by_id(999)
        
        assert result is None
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE id = ?",
            (999,)
        )
    
    # Test get_by_code method
    def test_get_by_code_returns_child(self, service, mock_db):
        """Test getting child by code"""
        expected_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = expected_child
        
        result = service.get_by_code('AS001')
        
        assert result == expected_child
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE code = ?",
            ('AS001',)
        )
    
    def test_get_by_code_returns_none_for_invalid_code(self, service, mock_db):
        """Test get_by_code returns None for non-existent code"""
        mock_db.fetchone.return_value = None
        
        result = service.get_by_code('INVALID')
        
        assert result is None
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE code = ?",
            ('INVALID',)
        )
    
    # Test create method
    def test_create_child_success(self, service, mock_db):
        """Test successfully creating a new child"""
        mock_db.fetchone.return_value = None  # No existing child
        mock_db.insert.return_value = 42  # New child ID
        
        result = service.create('Alice Smith', 'AS001', active=True)
        
        assert result == 42
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE code = ?",
            ('AS001',)
        )
        mock_db.insert.assert_called_once_with(
            "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
            ('Alice Smith', 'AS001', True)
        )
    
    def test_create_child_with_duplicate_code_raises_error(self, service, mock_db):
        """Test creating child with duplicate code raises ValueError"""
        existing_child = {
            'id': 1, 'name': 'Existing Child', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        with pytest.raises(ValueError, match="Child with code 'AS001' already exists"):
            service.create('Alice Smith', 'AS001')
        
        mock_db.fetchone.assert_called_once()
        mock_db.insert.assert_not_called()
    
    def test_create_child_defaults_to_active(self, service, mock_db):
        """Test create child defaults to active=True"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        result = service.create('Alice Smith', 'AS001')
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
            ('Alice Smith', 'AS001', True)
        )
    
    def test_create_inactive_child(self, service, mock_db):
        """Test creating an inactive child"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        result = service.create('Alice Smith', 'AS001', active=False)
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
            ('Alice Smith', 'AS001', False)
        )
    
    # Test update method
    def test_update_child_name(self, service, mock_db):
        """Test updating child's name"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.update(1, {'name': 'Alice Johnson'})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET name = ? WHERE id = ?",
            ['Alice Johnson', 1]
        )
    
    def test_update_child_code(self, service, mock_db):
        """Test updating child's code"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_child, None]  # First call returns child, second returns None
        
        result = service.update(1, {'code': 'AJ002'})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET code = ? WHERE id = ?",
            ['AJ002', 1]
        )
    
    def test_update_child_code_duplicate_raises_error(self, service, mock_db):
        """Test updating to duplicate code raises ValueError"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        another_child = {
            'id': 2, 'name': 'Bob Jones', 'code': 'BJ002', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_child, another_child]
        
        with pytest.raises(ValueError, match="Child with code 'BJ002' already exists"):
            service.update(1, {'code': 'BJ002'})
        
        mock_db.execute.assert_not_called()
    
    def test_update_child_active_status(self, service, mock_db):
        """Test updating child's active status"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.update(1, {'active': 0})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET active = ? WHERE id = ?",
            [0, 1]
        )
    
    def test_update_multiple_fields(self, service, mock_db):
        """Test updating multiple fields at once"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.side_effect = [existing_child, None]
        
        result = service.update(1, {
            'name': 'Alice Johnson',
            'code': 'AJ002',
            'active': 0
        })
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET name = ?, code = ?, active = ? WHERE id = ?",
            ['Alice Johnson', 'AJ002', 0, 1]
        )
    
    def test_update_nonexistent_child_returns_false(self, service, mock_db):
        """Test updating non-existent child returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.update(999, {'name': 'New Name'})
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_update_with_no_changes_returns_true(self, service, mock_db):
        """Test update with empty data returns True without DB call"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.update(1, {})
        
        assert result is True
        mock_db.execute.assert_not_called()
    
    def test_update_same_code_succeeds(self, service, mock_db):
        """Test updating with same code succeeds"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.update(1, {'code': 'AS001', 'name': 'Alice Johnson'})
        
        assert result is True
        # Should update both fields even though code is unchanged
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET name = ?, code = ? WHERE id = ?",
            ['Alice Johnson', 'AS001', 1]
        )
    
    # Test deactivate method
    def test_deactivate_child_success(self, service, mock_db):
        """Test successfully deactivating a child"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 1
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.deactivate(1)
        
        assert result is True
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE id = ?",
            (1,)
        )
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_already_inactive_child(self, service, mock_db):
        """Test deactivating already inactive child still succeeds"""
        existing_child = {
            'id': 1, 'name': 'Alice Smith', 'code': 'AS001', 'active': 0
        }
        mock_db.fetchone.return_value = existing_child
        
        result = service.deactivate(1)
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE children SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_nonexistent_child_returns_false(self, service, mock_db):
        """Test deactivating non-existent child returns False"""
        mock_db.fetchone.return_value = None
        
        result = service.deactivate(999)
        
        assert result is False
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM children WHERE id = ?",
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
        """Test creating child with empty strings"""
        mock_db.fetchone.return_value = None
        mock_db.insert.side_effect = Exception("NOT NULL constraint failed")
        
        with pytest.raises(Exception, match="NOT NULL constraint failed"):
            service.create('', '')
    
    def test_create_with_none_values_raises_database_error(self, service, mock_db):
        """Test creating child with None values"""
        mock_db.fetchone.return_value = None
        mock_db.insert.side_effect = Exception("NOT NULL constraint failed")
        
        with pytest.raises(Exception, match="NOT NULL constraint failed"):
            service.create(None, None)
    
    def test_code_case_sensitivity(self, service, mock_db):
        """Test that codes are case-sensitive"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        # Create with uppercase code
        result = service.create('Alice Smith', 'AS001')
        assert result == 1
        
        # Searching for lowercase should not find it (assuming case-sensitive DB)
        mock_db.fetchone.return_value = None
        result = service.get_by_code('as001')
        assert result is None