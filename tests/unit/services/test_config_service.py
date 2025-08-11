"""Unit tests for ConfigService"""

import pytest
from unittest.mock import Mock
from services.config_service import ConfigService


class TestConfigService:
    """Test suite for ConfigService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a ConfigService instance with mock database"""
        return ConfigService(mock_db)
    
    @pytest.fixture
    def sample_hour_limit(self):
        """Sample hour limit data"""
        return {
            'id': 1,
            'employee_id': 1,
            'employee_name': 'John Doe',
            'child_id': 1,
            'child_name': 'Jane Smith',
            'max_hours_per_week': 20.0,
            'alert_threshold': 18.0,
            'active': 1
        }
    
    # Test hour limits management
    def test_get_all_hour_limits(self, service, mock_db, sample_hour_limit):
        """Test retrieving all hour limits"""
        mock_db.fetchall.return_value = [sample_hour_limit]
        
        result = service.get_all_hour_limits()
        
        # Verify query includes joins
        call_args = mock_db.fetchall.call_args[0][0]
        assert 'JOIN employees e' in call_args
        assert 'JOIN children c' in call_args
        assert 'ORDER BY e.friendly_name, c.name' in call_args
        assert result == [sample_hour_limit]
    
    def test_get_all_hour_limits_active_only(self, service, mock_db):
        """Test retrieving only active hour limits"""
        mock_db.fetchall.return_value = []
        
        service.get_all_hour_limits(active_only=True)
        
        call_args = mock_db.fetchall.call_args[0][0]
        assert 'WHERE h.active = 1' in call_args
    
    def test_get_hour_limit(self, service, mock_db, sample_hour_limit):
        """Test retrieving specific hour limit"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.get_hour_limit(1, 1)
        
        mock_db.fetchone.assert_called_once_with(
            """SELECT * FROM hour_limits
               WHERE employee_id = ? AND child_id = ? AND active = 1""",
            (1, 1)
        )
        assert result == sample_hour_limit
    
    def test_get_hour_limit_not_found(self, service, mock_db):
        """Test retrieving non-existent hour limit"""
        mock_db.fetchone.return_value = None
        
        result = service.get_hour_limit(999, 999)
        
        assert result is None
    
    # Test create_hour_limit
    def test_create_hour_limit_success(self, service, mock_db):
        """Test creating hour limit successfully"""
        mock_db.fetchone.return_value = None  # No existing limit
        mock_db.insert.return_value = 1
        
        result = service.create_hour_limit(1, 1, 20.0, 18.0)
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            """INSERT INTO hour_limits (employee_id, child_id, max_hours_per_week, alert_threshold)
               VALUES (?, ?, ?, ?)""",
            (1, 1, 20.0, 18.0)
        )
    
    def test_create_hour_limit_already_exists(self, service, mock_db, sample_hour_limit):
        """Test creating hour limit when one already exists"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        with pytest.raises(ValueError, match="Hour limit already exists"):
            service.create_hour_limit(1, 1, 20.0)
    
    def test_create_hour_limit_invalid_threshold(self, service, mock_db):
        """Test creating hour limit with invalid alert threshold"""
        mock_db.fetchone.return_value = None
        
        with pytest.raises(ValueError, match="Alert threshold must be less than max hours"):
            service.create_hour_limit(1, 1, 20.0, 25.0)
    
    def test_create_hour_limit_equal_threshold(self, service, mock_db):
        """Test creating hour limit with threshold equal to max"""
        mock_db.fetchone.return_value = None
        
        with pytest.raises(ValueError, match="Alert threshold must be less than max hours"):
            service.create_hour_limit(1, 1, 20.0, 20.0)
    
    def test_create_hour_limit_no_threshold(self, service, mock_db):
        """Test creating hour limit without alert threshold"""
        mock_db.fetchone.return_value = None
        mock_db.insert.return_value = 1
        
        result = service.create_hour_limit(1, 1, 20.0)
        
        assert result == 1
        # Verify None was passed for threshold
        call_args = mock_db.insert.call_args[0]
        assert call_args[1][3] is None
    
    # Test update_hour_limit
    def test_update_hour_limit_max_hours(self, service, mock_db, sample_hour_limit):
        """Test updating max hours per week"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.update_hour_limit(1, {'max_hours_per_week': 25.0})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE hour_limits SET max_hours_per_week = ? WHERE id = ?",
            [25.0, 1]
        )
    
    def test_update_hour_limit_alert_threshold(self, service, mock_db, sample_hour_limit):
        """Test updating alert threshold"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.update_hour_limit(1, {'alert_threshold': 15.0})
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE hour_limits SET alert_threshold = ? WHERE id = ?",
            [15.0, 1]
        )
    
    def test_update_hour_limit_multiple_fields(self, service, mock_db, sample_hour_limit):
        """Test updating multiple fields at once"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.update_hour_limit(1, {
            'max_hours_per_week': 25.0,
            'alert_threshold': 22.0,
            'active': 0
        })
        
        assert result is True
        call_args = mock_db.execute.call_args[0]
        assert 'max_hours_per_week = ?' in call_args[0]
        assert 'alert_threshold = ?' in call_args[0]
        assert 'active = ?' in call_args[0]
        assert call_args[1] == [25.0, 22.0, 0, 1]
    
    def test_update_hour_limit_invalid_threshold(self, service, mock_db, sample_hour_limit):
        """Test updating with invalid alert threshold"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        with pytest.raises(ValueError, match="Alert threshold must be less than max hours"):
            service.update_hour_limit(1, {
                'max_hours_per_week': 15.0,
                'alert_threshold': 20.0
            })
    
    def test_update_hour_limit_threshold_exceeds_existing_max(self, service, mock_db, sample_hour_limit):
        """Test updating threshold to exceed existing max hours"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        with pytest.raises(ValueError, match="Alert threshold must be less than max hours"):
            service.update_hour_limit(1, {'alert_threshold': 25.0})
    
    def test_update_hour_limit_not_found(self, service, mock_db):
        """Test updating non-existent hour limit"""
        mock_db.fetchone.return_value = None
        
        result = service.update_hour_limit(999, {'max_hours_per_week': 25.0})
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    def test_update_hour_limit_no_changes(self, service, mock_db, sample_hour_limit):
        """Test update with empty data"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.update_hour_limit(1, {})
        
        assert result is True
        mock_db.execute.assert_not_called()
    
    # Test deactivate_hour_limit
    def test_deactivate_hour_limit_success(self, service, mock_db, sample_hour_limit):
        """Test deactivating hour limit"""
        mock_db.fetchone.return_value = sample_hour_limit
        
        result = service.deactivate_hour_limit(1)
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE hour_limits SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_hour_limit_not_found(self, service, mock_db):
        """Test deactivating non-existent hour limit"""
        mock_db.fetchone.return_value = None
        
        result = service.deactivate_hour_limit(999)
        
        assert result is False
        mock_db.execute.assert_not_called()
    
    # Test app settings management
    def test_get_app_settings(self, service, mock_db):
        """Test retrieving all app settings"""
        settings = [
            {'key': 'timezone', 'value': 'America/Chicago'},
            {'key': 'date_format', 'value': '%Y-%m-%d'},
            {'key': 'max_hours_per_day', 'value': '12'}
        ]
        mock_db.fetchall.return_value = settings
        
        result = service.get_app_settings()
        
        assert result == {
            'timezone': 'America/Chicago',
            'date_format': '%Y-%m-%d',
            'max_hours_per_day': '12'
        }
    
    def test_get_app_settings_empty(self, service, mock_db):
        """Test retrieving settings when none exist"""
        mock_db.fetchall.return_value = []
        
        result = service.get_app_settings()
        
        assert result == {}
    
    def test_update_app_settings(self, service, mock_db):
        """Test updating multiple app settings"""
        settings = {
            'timezone': 'America/New_York',
            'date_format': '%m/%d/%Y',
            'new_setting': 'value'
        }
        
        service.update_app_settings(settings)
        
        assert mock_db.execute.call_count == 3
        
        # Verify each setting was updated
        calls = mock_db.execute.call_args_list
        for call in calls:
            assert call[0][0] == "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)"
            assert call[0][1][0] in settings
            assert call[0][1][1] == settings[call[0][1][0]]
    
    def test_update_app_settings_empty(self, service, mock_db):
        """Test updating with empty settings dict"""
        service.update_app_settings({})
        
        mock_db.execute.assert_not_called()
    
    def test_get_setting(self, service, mock_db):
        """Test retrieving single setting"""
        mock_db.fetchone.return_value = {'value': 'America/Chicago'}
        
        result = service.get_setting('timezone')
        
        mock_db.fetchone.assert_called_once_with(
            "SELECT value FROM app_config WHERE key = ?",
            ('timezone',)
        )
        assert result == 'America/Chicago'
    
    def test_get_setting_not_found(self, service, mock_db):
        """Test retrieving non-existent setting"""
        mock_db.fetchone.return_value = None
        
        result = service.get_setting('non_existent')
        
        assert result is None
    
    def test_set_setting(self, service, mock_db):
        """Test setting single configuration value"""
        service.set_setting('timezone', 'America/New_York')
        
        mock_db.execute.assert_called_once_with(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            ('timezone', 'America/New_York')
        )
    
    def test_set_setting_numeric_value(self, service, mock_db):
        """Test setting numeric configuration value"""
        service.set_setting('max_hours', 40)
        
        mock_db.execute.assert_called_once_with(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            ('max_hours', 40)
        )
    
    def test_set_setting_none_value(self, service, mock_db):
        """Test setting None as configuration value"""
        service.set_setting('optional_setting', None)
        
        mock_db.execute.assert_called_once_with(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            ('optional_setting', None)
        )


class TestConfigServiceIntegration:
    """Integration tests for ConfigService with real database"""
    
    def test_hour_limits_crud_operations(self, test_db, sample_data):
        """Test complete CRUD operations for hour limits"""
        service = ConfigService(test_db)
        
        # Create hour limit
        limit_id = service.create_hour_limit(
            sample_data['employee'].id,
            sample_data['child'].id,
            20.0,
            18.0
        )
        assert limit_id is not None
        
        # Read hour limit
        limit = service.get_hour_limit(
            sample_data['employee'].id,
            sample_data['child'].id
        )
        assert limit is not None
        assert limit['max_hours_per_week'] == 20.0
        assert limit['alert_threshold'] == 18.0
        
        # Update hour limit
        result = service.update_hour_limit(limit_id, {
            'max_hours_per_week': 25.0,
            'alert_threshold': 22.0
        })
        assert result is True
        
        # Verify update
        updated = service.get_hour_limit(
            sample_data['employee'].id,
            sample_data['child'].id
        )
        assert updated['max_hours_per_week'] == 25.0
        assert updated['alert_threshold'] == 22.0
        
        # Deactivate hour limit
        result = service.deactivate_hour_limit(limit_id)
        assert result is True
        
        # Verify deactivation
        inactive = service.get_hour_limit(
            sample_data['employee'].id,
            sample_data['child'].id
        )
        assert inactive is None  # get_hour_limit only returns active limits
    
    def test_app_settings_persistence(self, test_db):
        """Test app settings are persisted correctly"""
        service = ConfigService(test_db)
        
        # Set initial settings
        settings = {
            'test_key1': 'value1',
            'test_key2': 'value2',
            'test_numeric': '42'
        }
        service.update_app_settings(settings)
        
        # Retrieve settings
        retrieved = service.get_app_settings()
        assert 'test_key1' in retrieved
        assert retrieved['test_key1'] == 'value1'
        assert retrieved['test_numeric'] == '42'
        
        # Update single setting
        service.set_setting('test_key1', 'updated_value')
        
        # Verify update
        value = service.get_setting('test_key1')
        assert value == 'updated_value'
        
        # Verify other settings unchanged
        value = service.get_setting('test_key2')
        assert value == 'value2'
    
    def test_hour_limit_validation_integration(self, test_db, sample_data):
        """Test hour limit validation rules with real database"""
        service = ConfigService(test_db)
        
        # Create valid hour limit
        limit_id = service.create_hour_limit(
            sample_data['employee'].id,
            sample_data['child'].id,
            20.0,
            15.0
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            service.create_hour_limit(
                sample_data['employee'].id,
                sample_data['child'].id,
                30.0
            )
        
        # Try to update with invalid threshold
        with pytest.raises(ValueError, match="must be less than"):
            service.update_hour_limit(limit_id, {'alert_threshold': 25.0})