"""
Unit tests for ShiftService hour limits and remaining methods
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date, time, timedelta
from services.shift_service import ShiftService


class TestShiftServiceHourLimits:
    """Test suite for ShiftService hour limits and error handling"""
    
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
                service = ShiftService(mock_db)
                service.config_service = mock_config_service
                service.payroll_service = mock_payroll_service
                return service
    
    # Test check_hour_limits method
    def test_check_hour_limits_no_limit_configured(self, service, mock_config_service):
        """Test returns None when no hour limit is configured"""
        mock_config_service.get_hour_limit.return_value = None
        
        result = service.check_hour_limits(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result is None
        mock_config_service.get_hour_limit.assert_called_once_with(1, 2)
    
    def test_check_hour_limits_no_payroll_period(self, service, mock_config_service, mock_payroll_service):
        """Test returns None when no payroll period found"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = None
        
        result = service.check_hour_limits(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result is None
        mock_payroll_service.get_period_for_date.assert_called_once_with('2024-01-08')
    
    def test_check_hour_limits_week_1_under_limit(self, service, mock_config_service, mock_payroll_service):
        """Test week 1 hours under limit returns None"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',  # Thursday
            'end_date': '2024-01-17'     # Wednesday
        }
        # Mock existing hours (20) + new shift (8) = 28 hours, under limit
        service.calculate_period_hours = Mock(return_value=20)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',  # Monday, week 1
            '09:00:00', '17:00:00'  # 8 hours
        )
        
        assert result is None
        service.calculate_period_hours.assert_called_once_with(
            1, 2, '2024-01-04', '2024-01-10', None
        )
    
    def test_check_hour_limits_week_2_under_limit(self, service, mock_config_service, mock_payroll_service):
        """Test week 2 hours under limit returns None"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',  # Thursday
            'end_date': '2024-01-17'     # Wednesday
        }
        # Mock existing hours (25) + new shift (8) = 33 hours, under limit
        service.calculate_period_hours = Mock(return_value=25)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-15',  # Monday, week 2 (day 11)
            '09:00:00', '17:00:00'  # 8 hours
        )
        
        assert result is None
        service.calculate_period_hours.assert_called_once_with(
            1, 2, '2024-01-11', '2024-01-17', None
        )
    
    def test_check_hour_limits_week_1_exceeds_max(self, service, mock_config_service, mock_payroll_service):
        """Test week 1 exceeding max hours returns warning"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours (35) + new shift (8) = 43 hours, exceeds 40
        service.calculate_period_hours = Mock(return_value=35)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '17:00:00'
        )
        
        assert result == "Week 1 hours (43.0) exceeds weekly limit (40.0) for this employee/child pair"
    
    def test_check_hour_limits_week_2_exceeds_max(self, service, mock_config_service, mock_payroll_service):
        """Test week 2 exceeding max hours returns warning"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours (38) + new shift (5) = 43 hours, exceeds 40
        service.calculate_period_hours = Mock(return_value=38)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-12',  # Friday, week 2
            '09:00:00', '14:00:00'  # 5 hours
        )
        
        assert result == "Week 2 hours (43.0) exceeds weekly limit (40.0) for this employee/child pair"
    
    def test_check_hour_limits_exceeds_alert_threshold(self, service, mock_config_service, mock_payroll_service):
        """Test exceeding alert threshold but not max returns threshold warning"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours (30) + new shift (7) = 37 hours, exceeds threshold 35 but not max 40
        service.calculate_period_hours = Mock(return_value=30)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '16:00:00'  # 7 hours
        )
        
        assert result == "Week 1 hours (37.0) exceeds alert threshold (35.0) for this employee/child pair"
    
    def test_check_hour_limits_no_alert_threshold(self, service, mock_config_service, mock_payroll_service):
        """Test with no alert threshold set"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': None  # No threshold
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours (30) + new shift (8) = 38 hours, under max
        service.calculate_period_hours = Mock(return_value=30)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '17:00:00'
        )
        
        assert result is None  # No warning since no threshold and under max
    
    def test_check_hour_limits_exact_boundary(self, service, mock_config_service, mock_payroll_service):
        """Test exact hour limit boundary (40.0 == 40.0)"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours (32) + new shift (8) = exactly 40 hours
        service.calculate_period_hours = Mock(return_value=32)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '17:00:00'
        )
        
        # Should exceed threshold (40 > 35) but not max (40 == 40)
        assert result == "Week 1 hours (40.0) exceeds alert threshold (35.0) for this employee/child pair"
    
    def test_check_hour_limits_with_exclude_shift(self, service, mock_config_service, mock_payroll_service):
        """Test hour limits calculation with excluded shift ID"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        service.calculate_period_hours = Mock(return_value=20)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '17:00:00',
            exclude_shift_id=5
        )
        
        assert result is None
        service.calculate_period_hours.assert_called_once_with(
            1, 2, '2024-01-04', '2024-01-10', 5
        )
    
    def test_check_hour_limits_floating_point_precision(self, service, mock_config_service, mock_payroll_service):
        """Test floating point precision handling with rounding"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40.0,
            'alert_threshold': 35.0
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        # Mock existing hours with floating point precision issues
        service.calculate_period_hours = Mock(return_value=34.999999999)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '14:30:00'  # 5.5 hours
        )
        
        # 34.999999999 + 5.5 = 40.499999999, rounds to 40.5, exceeds 40.0
        assert "Week 1 hours (40.5) exceeds weekly limit (40.0)" in result
    
    def test_check_hour_limits_week_boundary_detection(self, service, mock_config_service, mock_payroll_service):
        """Test correct week detection at period boundaries"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',  # Thursday
            'end_date': '2024-01-17'     # Wednesday
        }
        service.calculate_period_hours = Mock(return_value=20)
        
        # Test day 6 (Wednesday) - should be week 1
        result = service.check_hour_limits(
            1, 2, '2024-01-10',  # Day 6 of period
            '09:00:00', '17:00:00'
        )
        assert result is None
        service.calculate_period_hours.assert_called_with(
            1, 2, '2024-01-04', '2024-01-10', None
        )
        
        # Reset mock
        service.calculate_period_hours.reset_mock()
        
        # Test day 7 (Thursday) - should be week 2
        result = service.check_hour_limits(
            1, 2, '2024-01-11',  # Day 7 of period
            '09:00:00', '17:00:00'
        )
        assert result is None
        service.calculate_period_hours.assert_called_with(
            1, 2, '2024-01-11', '2024-01-17', None
        )
    
    def test_check_hour_limits_partial_hours(self, service, mock_config_service, mock_payroll_service):
        """Test hour limits with partial hours (minutes)"""
        mock_config_service.get_hour_limit.return_value = {
            'max_hours_per_week': 40,
            'alert_threshold': 35
        }
        mock_payroll_service.get_period_for_date.return_value = {
            'start_date': '2024-01-04',
            'end_date': '2024-01-17'
        }
        service.calculate_period_hours = Mock(return_value=39.5)
        
        result = service.check_hour_limits(
            1, 2, '2024-01-08',
            '09:00:00', '09:45:00'  # 0.75 hours
        )
        
        # 39.5 + 0.75 = 40.25 hours, exceeds 40
        assert "Week 1 hours (40.2) exceeds weekly limit (40.0)" in result
    
    # Test error handling in validate_shift
    def test_validate_shift_employee_db_error_fallback(self, service, mock_db):
        """Test validate_shift handles database error for employee lookup"""
        # Mock the methods called by validate_shift
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={
            'employee': {
                'id': 10,
                'start_time': '08:00:00',
                'end_time': '12:00:00'
            },
            'child': None
        })
        service.check_hour_limits = Mock(return_value=None)
        service.format_time_for_display = Mock(side_effect=['8:00 AM', '12:00 PM'])
        
        # Mock database error when fetching employee name
        mock_db.fetchone.side_effect = Exception("Database error")
        
        with pytest.raises(ValueError) as exc_info:
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        # Should fall back to "Employee #1"
        assert "Employee #1 already has an overlapping shift" in str(exc_info.value)
    
    def test_validate_shift_child_db_error_fallback(self, service, mock_db):
        """Test validate_shift handles database error for child lookup"""
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={
            'employee': None,
            'child': {
                'id': 11,
                'start_time': '14:00:00',
                'end_time': '18:00:00'
            }
        })
        service.check_hour_limits = Mock(return_value=None)
        service.format_time_for_display = Mock(side_effect=['2:00 PM', '6:00 PM'])
        
        # Mock database error when fetching child name
        mock_db.fetchone.side_effect = Exception("Database error")
        
        with pytest.raises(ValueError) as exc_info:
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        # Should fall back to "Child #2"
        assert "Child #2 already has an overlapping shift" in str(exc_info.value)
    
    def test_validate_shift_both_lookups_fail(self, service, mock_db):
        """Test validate_shift handles both employee and child lookup failures"""
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={
            'employee': {
                'id': 10,
                'start_time': '08:00:00',
                'end_time': '12:00:00'
            },
            'child': {
                'id': 11,
                'start_time': '14:00:00',
                'end_time': '18:00:00'
            }
        })
        service.check_hour_limits = Mock(return_value=None)
        service.format_time_for_display = Mock(side_effect=[
            '8:00 AM', '12:00 PM', '2:00 PM', '6:00 PM'
        ])
        
        # Mock database errors for both lookups
        mock_db.fetchone.side_effect = [
            Exception("DB error 1"),  # Employee lookup fails
            Exception("DB error 2")   # Child lookup fails
        ]
        
        # Should raise error for employee overlap first
        with pytest.raises(ValueError) as exc_info:
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert "Employee #1 already has an overlapping shift" in str(exc_info.value)