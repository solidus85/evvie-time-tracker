"""
Unit tests for ShiftService validation and conflict detection
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, date, time
from services.shift_service import ShiftService


class TestShiftServiceValidation:
    """Test suite for ShiftService validation methods"""
    
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
                # Replace config_service with our mock
                service.config_service = mock_config_service
                return service
    
    # Test validate_shift method
    def test_validate_shift_valid_no_conflicts(self, service, mock_db, mock_config_service):
        """Test validation passes for a valid shift with no conflicts"""
        # Mock no exclusions, no overlaps, no hour limits
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value=None)
        
        warnings = service.validate_shift(
            employee_id=1,
            child_id=2,
            date='2024-01-08',
            start_time='09:00:00',
            end_time='17:00:00'
        )
        
        assert warnings == []
        service.check_exclusions.assert_called_once_with(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        service.check_overlaps.assert_called_once_with(1, 2, '2024-01-08', '09:00:00', '17:00:00', None)
        service.check_hour_limits.assert_called_once_with(1, 2, '2024-01-08', '09:00:00', '17:00:00', None)
    
    def test_validate_shift_start_time_after_end_time_raises_error(self, service):
        """Test validation fails when start time is after end time"""
        with pytest.raises(ValueError, match="End time must be after start time"):
            service.validate_shift(1, 2, '2024-01-08', '17:00:00', '09:00:00')
    
    def test_validate_shift_start_time_equals_end_time_raises_error(self, service):
        """Test validation fails when start time equals end time"""
        with pytest.raises(ValueError, match="End time must be after start time"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '09:00:00')
    
    def test_validate_shift_employee_exclusion_raises_error(self, service):
        """Test validation fails for employee exclusion period"""
        exclusion = {
            'id': 1,
            'name': 'Employee Vacation',
            'employee_id': 1,
            'child_id': None,
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        service.check_exclusions = Mock(return_value=[exclusion])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="Employee is excluded during this period: Employee Vacation"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    def test_validate_shift_child_exclusion_raises_error(self, service):
        """Test validation fails for child exclusion period"""
        exclusion = {
            'id': 1,
            'name': 'Child Holiday',
            'employee_id': None,
            'child_id': 2,
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        service.check_exclusions = Mock(return_value=[exclusion])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="Child is excluded during this period: Child Holiday"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    def test_validate_shift_general_exclusion_adds_warning(self, service):
        """Test general exclusion adds warning but doesn't fail"""
        exclusion = {
            'id': 1,
            'name': 'Office Closed',
            'employee_id': None,
            'child_id': None,
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        }
        service.check_exclusions = Mock(return_value=[exclusion])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value=None)
        
        warnings = service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(warnings) == 1
        assert "General exclusion period active: Office Closed" in warnings[0]
    
    def test_validate_shift_employee_overlap_raises_error(self, service, mock_db):
        """Test validation fails for employee overlap without allow_overlaps"""
        mock_db.fetchone.return_value = {'friendly_name': 'John Doe'}
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
        
        with pytest.raises(ValueError, match="John Doe already has an overlapping shift from 8:00 AM to 12:00 PM on this date"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    def test_validate_shift_employee_overlap_with_allow_overlaps_adds_warning(self, service, mock_db):
        """Test employee overlap adds warning when allow_overlaps is True"""
        mock_db.fetchone.return_value = {'friendly_name': 'John Doe'}
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
        
        warnings = service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00', allow_overlaps=True)
        
        assert len(warnings) == 1
        assert "John Doe already has an overlapping shift from 8:00 AM to 12:00 PM on this date" in warnings[0]
    
    def test_validate_shift_child_overlap_raises_error(self, service, mock_db):
        """Test validation fails for child overlap without allow_overlaps"""
        mock_db.fetchone.return_value = {'name': 'Alice Smith'}
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
        
        with pytest.raises(ValueError, match="Alice Smith already has an overlapping shift from 2:00 PM to 6:00 PM on this date"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    def test_validate_shift_hour_limit_warning(self, service):
        """Test hour limit warning is added to warnings list"""
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value="Warning: Employee will exceed 40 hours this week")
        
        warnings = service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(warnings) == 1
        assert "Warning: Employee will exceed 40 hours this week" in warnings[0]
    
    def test_validate_shift_multiple_warnings(self, service):
        """Test multiple warnings are accumulated"""
        general_exclusion = {
            'id': 1,
            'name': 'Holiday Period',
            'employee_id': None,
            'child_id': None
        }
        service.check_exclusions = Mock(return_value=[general_exclusion])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value="Approaching weekly hour limit")
        
        warnings = service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(warnings) == 2
        assert any("General exclusion period active: Holiday Period" in w for w in warnings)
        assert any("Approaching weekly hour limit" in w for w in warnings)
    
    def test_validate_shift_with_exclude_shift_id(self, service):
        """Test exclude_shift_id is passed through to validation methods"""
        service.check_exclusions = Mock(return_value=[])
        service.check_overlaps = Mock(return_value={'employee': None, 'child': None})
        service.check_hour_limits = Mock(return_value=None)
        
        service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00', exclude_shift_id=5)
        
        service.check_overlaps.assert_called_once_with(1, 2, '2024-01-08', '09:00:00', '17:00:00', 5)
        service.check_hour_limits.assert_called_once_with(1, 2, '2024-01-08', '09:00:00', '17:00:00', 5)
    
    def test_validate_shift_handles_format_time_error(self, service, mock_db):
        """Test validation handles time formatting errors gracefully"""
        mock_db.fetchone.return_value = {'friendly_name': 'John Doe'}
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
        service.format_time_for_display = Mock(side_effect=Exception("Format error"))
        
        # Should fall back to raw time strings
        with pytest.raises(ValueError, match="John Doe already has an overlapping shift from 08:00:00 to 12:00:00 on this date"):
            service.validate_shift(1, 2, '2024-01-08', '09:00:00', '17:00:00')
    
    # Test check_overlaps method
    def test_check_overlaps_no_overlaps(self, service, mock_db):
        """Test check_overlaps returns empty when no overlaps exist"""
        mock_db.fetchall.return_value = []
        
        result = service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result == {'employee': None, 'child': None}
        assert mock_db.fetchall.called
    
    def test_check_overlaps_employee_overlap(self, service, mock_db):
        """Test check_overlaps detects employee overlap"""
        overlap = {
            'id': 10,
            'employee_id': 1,
            'child_id': 3,
            'start_time': '08:00:00',
            'end_time': '12:00:00'
        }
        mock_db.fetchall.return_value = [overlap]
        
        result = service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result['employee'] == overlap
        assert result['child'] is None
    
    def test_check_overlaps_child_overlap(self, service, mock_db):
        """Test check_overlaps detects child overlap"""
        overlap = {
            'id': 11,
            'employee_id': 3,
            'child_id': 2,
            'start_time': '14:00:00',
            'end_time': '18:00:00'
        }
        mock_db.fetchall.return_value = [overlap]
        
        result = service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result['employee'] is None
        assert result['child'] == overlap
    
    def test_check_overlaps_both_overlaps(self, service, mock_db):
        """Test check_overlaps detects both employee and child overlaps"""
        overlaps = [
            {
                'id': 10,
                'employee_id': 1,
                'child_id': 3,
                'start_time': '08:00:00',
                'end_time': '12:00:00'
            },
            {
                'id': 11,
                'employee_id': 3,
                'child_id': 2,
                'start_time': '14:00:00',
                'end_time': '18:00:00'
            }
        ]
        mock_db.fetchall.return_value = overlaps
        
        result = service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result['employee'] == overlaps[0]
        assert result['child'] == overlaps[1]
    
    def test_check_overlaps_with_exclude_shift_id(self, service, mock_db):
        """Test check_overlaps excludes specified shift ID"""
        mock_db.fetchall.return_value = []
        
        service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00', exclude_shift_id=5)
        
        # Check that the query includes the exclude condition
        call_args = mock_db.fetchall.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "AND id != ?" in query
        assert 5 in params
    
    def test_check_overlaps_handles_string_ids(self, service, mock_db):
        """Test check_overlaps handles string IDs from database"""
        overlap = {
            'id': 10,
            'employee_id': '1',  # String from DB
            'child_id': '3',
            'start_time': '08:00:00',
            'end_time': '12:00:00'
        }
        mock_db.fetchall.return_value = [overlap]
        
        result = service.check_overlaps(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result['employee'] == overlap
        assert result['child'] is None
    
    # Test check_exclusions method
    def test_check_exclusions_no_exclusions(self, service, mock_db):
        """Test check_exclusions returns empty list when no exclusions"""
        mock_db.fetchall.return_value = []
        
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert result == []
        assert mock_db.fetchall.called
    
    def test_check_exclusions_date_only_exclusion(self, service, mock_db):
        """Test check_exclusions returns full-day exclusion"""
        exclusion = {
            'id': 1,
            'name': 'Holiday',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'start_time': None,
            'end_time': None,
            'employee_id': 1,
            'child_id': None
        }
        mock_db.fetchall.return_value = [exclusion]
        
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(result) == 1
        assert result[0] == exclusion
    
    def test_check_exclusions_time_overlap(self, service, mock_db):
        """Test check_exclusions detects time overlap"""
        exclusion = {
            'id': 1,
            'name': 'Lunch Break',
            'start_date': '2024-01-08',
            'end_date': '2024-01-08',
            'start_time': '12:00:00',
            'end_time': '13:00:00',
            'employee_id': 1,
            'child_id': None
        }
        mock_db.fetchall.return_value = [exclusion]
        
        # Shift from 09:00 to 17:00 overlaps with lunch 12:00-13:00
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(result) == 1
        assert result[0] == exclusion
    
    def test_check_exclusions_no_time_overlap(self, service, mock_db):
        """Test check_exclusions filters out non-overlapping times"""
        exclusion = {
            'id': 1,
            'name': 'Early Morning',
            'start_date': '2024-01-08',
            'end_date': '2024-01-08',
            'start_time': '05:00:00',
            'end_time': '07:00:00',
            'employee_id': 1,
            'child_id': None
        }
        mock_db.fetchall.return_value = [exclusion]
        
        # Shift from 09:00 to 17:00 doesn't overlap with 05:00-07:00
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(result) == 0
    
    def test_check_exclusions_multiple_exclusions(self, service, mock_db):
        """Test check_exclusions handles multiple exclusions"""
        exclusions = [
            {
                'id': 1,
                'name': 'Employee Vacation',
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'start_time': None,
                'end_time': None,
                'employee_id': 1,
                'child_id': None
            },
            {
                'id': 2,
                'name': 'Child Holiday',
                'start_date': '2024-01-08',
                'end_date': '2024-01-08',
                'start_time': '14:00:00',
                'end_time': '16:00:00',
                'employee_id': None,
                'child_id': 2
            }
        ]
        mock_db.fetchall.return_value = exclusions
        
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(result) == 2
        assert result[0] == exclusions[0]  # Full day exclusion
        assert result[1] == exclusions[1]  # Time overlap (14:00-16:00 within 09:00-17:00)
    
    def test_check_exclusions_edge_case_exact_boundaries(self, service, mock_db):
        """Test check_exclusions handles exact time boundaries"""
        exclusion = {
            'id': 1,
            'name': 'Morning Block',
            'start_date': '2024-01-08',
            'end_date': '2024-01-08',
            'start_time': '07:00:00',
            'end_time': '09:00:00',  # Ends exactly when shift starts
            'employee_id': 1,
            'child_id': None
        }
        mock_db.fetchall.return_value = [exclusion]
        
        # Shift from 09:00 to 17:00 shouldn't overlap (adjacent, not overlapping)
        result = service.check_exclusions(1, 2, '2024-01-08', '09:00:00', '17:00:00')
        
        assert len(result) == 0
    
    # Test format_time_for_display method
    def test_format_time_for_display_morning(self, service):
        """Test formatting morning time"""
        result = service.format_time_for_display('09:30:00')
        assert result == '9:30 AM'
    
    def test_format_time_for_display_afternoon(self, service):
        """Test formatting afternoon time"""
        result = service.format_time_for_display('14:45:00')
        assert result == '2:45 PM'
    
    def test_format_time_for_display_midnight(self, service):
        """Test formatting midnight"""
        result = service.format_time_for_display('00:00:00')
        assert result == '12:00 AM'
    
    def test_format_time_for_display_noon(self, service):
        """Test formatting noon"""
        result = service.format_time_for_display('12:00:00')
        assert result == '12:00 PM'
    
    def test_format_time_for_display_invalid_format(self, service):
        """Test format_time_for_display returns original on error"""
        result = service.format_time_for_display('invalid')
        assert result == 'invalid'
    
    def test_format_time_for_display_handles_leading_zero(self, service):
        """Test format_time_for_display removes leading zero"""
        result = service.format_time_for_display('08:00:00')
        assert result == '8:00 AM'
    
    # Test calculate_period_hours method
    def test_calculate_period_hours_no_shifts(self, service, mock_db):
        """Test calculate_period_hours returns 0 for no shifts"""
        mock_db.fetchone.return_value = {'total_hours': None}
        
        result = service.calculate_period_hours(1, 2, '2024-01-01', '2024-01-07')
        
        assert result == 0
    
    def test_calculate_period_hours_with_shifts(self, service, mock_db):
        """Test calculate_period_hours returns total hours"""
        mock_db.fetchone.return_value = {'total_hours': 40.5}
        
        result = service.calculate_period_hours(1, 2, '2024-01-01', '2024-01-07')
        
        assert result == 40.5
    
    def test_calculate_period_hours_with_exclude_shift(self, service, mock_db):
        """Test calculate_period_hours excludes specified shift"""
        mock_db.fetchone.return_value = {'total_hours': 32.0}
        
        service.calculate_period_hours(1, 2, '2024-01-01', '2024-01-07', exclude_shift_id=5)
        
        # Check that the query includes the exclude condition
        call_args = mock_db.fetchone.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "AND id != ?" in query
        assert 5 in params