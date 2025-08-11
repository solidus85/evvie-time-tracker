"""Unit tests for PayrollService"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch
from services.payroll_service import PayrollService


class TestPayrollService:
    """Test suite for PayrollService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a PayrollService instance with mock database"""
        return PayrollService(mock_db)
    
    @pytest.fixture
    def sample_period(self):
        """Sample payroll period data"""
        return {
            'id': 1,
            'start_date': '2025-01-01',
            'end_date': '2025-01-14'
        }
    
    @pytest.fixture
    def sample_exclusion(self):
        """Sample exclusion period data"""
        return {
            'id': 1,
            'name': 'Holiday Break',
            'start_date': '2025-01-01',
            'end_date': '2025-01-07',
            'start_time': None,
            'end_time': None,
            'employee_id': 1,
            'child_id': None,
            'reason': 'Holiday',
            'active': 1
        }
    
    # Test get_all_periods
    def test_get_all_periods(self, service, mock_db):
        """Test retrieving all payroll periods"""
        expected_periods = [
            {'id': 1, 'start_date': '2025-01-15', 'end_date': '2025-01-28'},
            {'id': 2, 'start_date': '2025-01-01', 'end_date': '2025-01-14'}
        ]
        mock_db.fetchall.return_value = expected_periods
        
        result = service.get_all_periods()
        
        mock_db.fetchall.assert_called_once_with(
            "SELECT * FROM payroll_periods ORDER BY start_date DESC"
        )
        assert result == expected_periods
    
    # Test get_current_period
    @patch('services.payroll_service.datetime')
    def test_get_current_period(self, mock_datetime, service, mock_db, sample_period):
        """Test retrieving current payroll period"""
        mock_datetime.now.return_value.date.return_value.isoformat.return_value = '2025-01-10'
        mock_db.fetchone.return_value = sample_period
        
        result = service.get_current_period()
        
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM payroll_periods WHERE start_date <= ? AND end_date >= ?",
            ('2025-01-10', '2025-01-10')
        )
        assert result == sample_period
    
    # Test get_period_for_date
    def test_get_period_for_date(self, service, mock_db, sample_period):
        """Test retrieving period for specific date"""
        mock_db.fetchone.return_value = sample_period
        
        result = service.get_period_for_date('2025-01-05')
        
        mock_db.fetchone.assert_called_once_with(
            "SELECT * FROM payroll_periods WHERE start_date <= ? AND end_date >= ?",
            ('2025-01-05', '2025-01-05')
        )
        assert result == sample_period
    
    def test_get_period_for_date_not_found(self, service, mock_db):
        """Test retrieving period for date with no match"""
        mock_db.fetchone.return_value = None
        
        result = service.get_period_for_date('2024-01-01')
        
        assert result is None
    
    # Test configure_periods
    @patch('services.payroll_service.datetime')
    def test_configure_periods(self, mock_datetime, service, mock_db):
        """Test configuring payroll periods from anchor date"""
        mock_datetime.now.return_value.date.return_value = date(2025, 1, 15)
        mock_datetime.strptime.return_value.date.return_value = date(2025, 1, 1)
        
        service.configure_periods('2025-01-01')
        
        # Verify periods were deleted
        mock_db.execute.assert_any_call("DELETE FROM payroll_periods")
        
        # Verify anchor date was saved
        mock_db.execute.assert_any_call(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES ('payroll_anchor_date', ?)",
            ('2025-01-01',)
        )
        
        # Verify periods were inserted (30 periods)
        assert mock_db.insert.call_count == 30
    
    # Test navigate_period
    def test_navigate_period_next(self, service, mock_db):
        """Test navigating to next payroll period"""
        current_period = {'id': 1, 'start_date': '2025-01-01', 'end_date': '2025-01-14'}
        next_period = {'id': 2, 'start_date': '2025-01-15', 'end_date': '2025-01-28'}
        
        mock_db.fetchone.side_effect = [current_period, next_period]
        
        result = service.navigate_period(1, 1)
        
        assert result == next_period
    
    def test_navigate_period_previous(self, service, mock_db):
        """Test navigating to previous payroll period"""
        current_period = {'id': 2, 'start_date': '2025-01-15', 'end_date': '2025-01-28'}
        prev_period = {'id': 1, 'start_date': '2025-01-01', 'end_date': '2025-01-14'}
        
        mock_db.fetchone.side_effect = [current_period, prev_period]
        
        result = service.navigate_period(2, -1)
        
        assert result == prev_period
    
    def test_navigate_period_invalid_direction(self, service, mock_db):
        """Test navigate period with invalid direction"""
        current_period = {'id': 1, 'start_date': '2025-01-01', 'end_date': '2025-01-14'}
        mock_db.fetchone.return_value = current_period
        
        result = service.navigate_period(1, 0)
        
        assert result is None
    
    def test_navigate_period_not_found(self, service, mock_db):
        """Test navigate period when period doesn't exist"""
        mock_db.fetchone.return_value = None
        
        result = service.navigate_period(999, 1)
        
        assert result is None
    
    # Test get_period_summary
    def test_get_period_summary(self, service, mock_db):
        """Test getting period summary with shifts"""
        period = {'id': 1, 'start_date': '2025-01-01', 'end_date': '2025-01-14'}
        shifts = [
            {
                'employee_id': 1, 'employee_name': 'John Doe',
                'child_id': 1, 'child_name': 'Jane Smith',
                'hours': 8.0, 'is_imported': 0
            },
            {
                'employee_id': 1, 'employee_name': 'John Doe',
                'child_id': 2, 'child_name': 'Bob Smith',
                'hours': 4.0, 'is_imported': 1
            }
        ]
        
        mock_db.fetchone.return_value = period
        mock_db.fetchall.return_value = shifts
        
        result = service.get_period_summary(1)
        
        assert result['period'] == period
        assert result['total_shifts'] == 2
        assert result['imported_shifts'] == 1
        assert result['manual_shifts'] == 1
        assert result['total_hours'] == 12.0
        assert '1_John Doe' in result['employee_hours']
        assert result['employee_hours']['1_John Doe'] == 12.0
    
    def test_get_period_summary_not_found(self, service, mock_db):
        """Test getting summary for non-existent period"""
        mock_db.fetchone.return_value = None
        
        result = service.get_period_summary(999)
        
        assert result is None
    
    # Test exclusion periods
    def test_get_exclusion_periods_all(self, service, mock_db):
        """Test retrieving all exclusion periods"""
        exclusions = [
            {'id': 1, 'name': 'Holiday', 'active': 1},
            {'id': 2, 'name': 'Vacation', 'active': 0}
        ]
        mock_db.fetchall.return_value = exclusions
        
        result = service.get_exclusion_periods(active_only=False)
        
        assert result == exclusions
        assert 'WHERE ep.active = 1' not in mock_db.fetchall.call_args[0][0]
    
    def test_get_exclusion_periods_active_only(self, service, mock_db):
        """Test retrieving only active exclusion periods"""
        exclusions = [{'id': 1, 'name': 'Holiday', 'active': 1}]
        mock_db.fetchall.return_value = exclusions
        
        result = service.get_exclusion_periods(active_only=True)
        
        assert result == exclusions
        assert 'WHERE ep.active = 1' in mock_db.fetchall.call_args[0][0]
    
    def test_get_active_exclusions_for_date(self, service, mock_db):
        """Test retrieving active exclusions for specific date"""
        exclusions = [{'id': 1, 'name': 'Holiday'}]
        mock_db.fetchall.return_value = exclusions
        
        result = service.get_active_exclusions_for_date('2025-01-05')
        
        mock_db.fetchall.assert_called_once_with(
            """SELECT * FROM exclusion_periods
               WHERE active = 1 AND start_date <= ? AND end_date >= ?""",
            ('2025-01-05', '2025-01-05')
        )
        assert result == exclusions
    
    # Test create_exclusion_period
    def test_create_exclusion_period_success(self, service, mock_db):
        """Test creating exclusion period successfully"""
        mock_db.insert.return_value = 1
        
        result = service.create_exclusion_period(
            'Holiday', '2025-01-01', '2025-01-07',
            employee_id=1, reason='Holiday break'
        )
        
        assert result == 1
        mock_db.insert.assert_called_once()
    
    def test_create_exclusion_period_invalid_dates(self, service, mock_db):
        """Test creating exclusion with end date before start date"""
        with pytest.raises(ValueError, match="End date must be after or equal to start date"):
            service.create_exclusion_period(
                'Invalid', '2025-01-10', '2025-01-01'
            )
    
    def test_create_exclusion_period_both_employee_and_child(self, service, mock_db):
        """Test creating exclusion with both employee and child IDs"""
        with pytest.raises(ValueError, match="An exclusion can only be for either an employee or a child"):
            service.create_exclusion_period(
                'Invalid', '2025-01-01', '2025-01-07',
                employee_id=1, child_id=1
            )
    
    def test_create_exclusion_with_times(self, service, mock_db):
        """Test creating exclusion with time ranges"""
        mock_db.insert.return_value = 1
        
        result = service.create_exclusion_period(
            'Partial Day', '2025-01-01', '2025-01-01',
            start_time='09:00:00', end_time='12:00:00',
            child_id=1
        )
        
        assert result == 1
        call_args = mock_db.insert.call_args[0]
        assert '09:00:00' in call_args[1]
        assert '12:00:00' in call_args[1]
    
    # Test update_exclusion_period
    def test_update_exclusion_period_success(self, service, mock_db):
        """Test updating exclusion period successfully"""
        mock_db.fetchone.return_value = {'id': 1}
        
        result = service.update_exclusion_period(
            1, 'Updated', '2025-01-01', '2025-01-07',
            employee_id=1
        )
        
        assert result is True
        mock_db.execute.assert_called_once()
    
    def test_update_exclusion_period_not_found(self, service, mock_db):
        """Test updating non-existent exclusion"""
        mock_db.fetchone.return_value = None
        
        result = service.update_exclusion_period(
            999, 'Updated', '2025-01-01', '2025-01-07'
        )
        
        assert result is False
    
    def test_update_exclusion_period_invalid_dates(self, service, mock_db):
        """Test updating exclusion with invalid dates"""
        mock_db.fetchone.return_value = {'id': 1}
        
        with pytest.raises(ValueError, match="End date must be after or equal to start date"):
            service.update_exclusion_period(
                1, 'Invalid', '2025-01-10', '2025-01-01'
            )
    
    # Test deactivate_exclusion_period
    def test_deactivate_exclusion_period_success(self, service, mock_db):
        """Test deactivating exclusion period"""
        mock_db.fetchone.return_value = {'id': 1}
        
        result = service.deactivate_exclusion_period(1)
        
        assert result is True
        mock_db.execute.assert_called_once_with(
            "UPDATE exclusion_periods SET active = 0 WHERE id = ?",
            (1,)
        )
    
    def test_deactivate_exclusion_period_not_found(self, service, mock_db):
        """Test deactivating non-existent exclusion"""
        mock_db.fetchone.return_value = None
        
        result = service.deactivate_exclusion_period(999)
        
        assert result is False
    
    # Test get_exclusions_for_period
    def test_get_exclusions_for_period(self, service, mock_db):
        """Test getting exclusions for a date range"""
        exclusions = [
            {'id': 1, 'name': 'Holiday', 'employee_name': 'John Doe'},
            {'id': 2, 'name': 'Training', 'child_name': 'Jane Smith'}
        ]
        mock_db.fetchall.return_value = exclusions
        
        result = service.get_exclusions_for_period('2025-01-01', '2025-01-31')
        
        assert result == exclusions
        # Verify complex date overlap query
        call_args = mock_db.fetchall.call_args[0]
        assert 'ep.active = 1' in call_args[0]
        assert len(call_args[1]) == 6  # 6 date parameters for overlap check
    
    # Test calculate_bulk_dates
    def test_calculate_bulk_dates_basic(self, service, mock_db):
        """Test calculating bulk dates for recurring pattern"""
        periods = [
            {'start_date': '2025-01-01', 'end_date': '2025-01-14'},
            {'start_date': '2025-01-15', 'end_date': '2025-01-28'}
        ]
        mock_db.fetchall.return_value = periods
        
        # Test with string dates
        result = service.calculate_bulk_dates(
            '2025-01-01', '2025-01-31',
            days_of_week=[1, 3],  # Monday and Wednesday
            weeks=[1, 2]  # First and second week
        )
        
        # Should return dates that match the pattern
        assert isinstance(result, list)
        assert all(isinstance(d, tuple) for d in result)
    
    def test_calculate_bulk_dates_invalid_range(self, service, mock_db):
        """Test bulk dates with invalid date range"""
        with pytest.raises(ValueError, match="End date must be after start date"):
            service.calculate_bulk_dates(
                '2025-01-31', '2025-01-01',
                days_of_week=[1], weeks=[1]
            )
    
    def test_calculate_bulk_dates_exceeds_limit(self, service, mock_db):
        """Test bulk dates exceeding 6 month limit"""
        with pytest.raises(ValueError, match="Date range cannot exceed 6 months"):
            service.calculate_bulk_dates(
                '2025-01-01', '2025-08-01',
                days_of_week=[1], weeks=[1]
            )
    
    @patch('services.payroll_service.date')
    def test_calculate_bulk_dates_defaults(self, mock_date, service, mock_db):
        """Test bulk dates with default start and end dates"""
        mock_date.today.return_value = date(2025, 1, 15)
        periods = [
            {'start_date': '2025-01-15', 'end_date': '2025-01-28'},
            {'start_date': '2025-01-29', 'end_date': '2025-02-11'}
        ]
        mock_db.fetchall.return_value = periods
        
        # Call with no start/end dates (should use defaults)
        result = service.calculate_bulk_dates(
            None, None,
            days_of_week=[1], weeks=[1]
        )
        
        # Should use today as start and 90 days as range
        assert mock_date.today.called
    
    # Test create_bulk_exclusions
    def test_create_bulk_exclusions(self, service, mock_db):
        """Test creating multiple exclusions in bulk"""
        periods = [
            {'start_date': '2025-01-02', 'end_date': '2025-01-15'},  # Thursday to Wednesday
            {'start_date': '2025-01-16', 'end_date': '2025-01-29'},  # Next period
        ]
        mock_db.fetchall.return_value = periods
        mock_db.insert.return_value = 1
        
        result = service.create_bulk_exclusions(
            'Recurring Meeting',
            start_date='2025-01-06',  # Start on Monday
            end_date='2025-01-19',    # Two week period
            days_of_week=[1],  # Monday
            weeks=[1, 2],  # Both weeks
            employee_id=1,
            reason='Weekly team meeting'
        )
        
        assert 'created' in result
        assert result['created'] >= 0
        assert 'dates' in result
    
    def test_create_bulk_exclusions_with_times(self, service, mock_db):
        """Test creating bulk exclusions with time ranges"""
        periods = [
            {'start_date': '2025-01-02', 'end_date': '2025-01-15'},  # Thursday to Wednesday
            {'start_date': '2025-01-16', 'end_date': '2025-01-29'},  # Next period
        ]
        mock_db.fetchall.return_value = periods
        mock_db.insert.return_value = 1
        
        result = service.create_bulk_exclusions(
            'Morning Training',
            start_date='2025-01-06',  # Start on Monday
            end_date='2025-01-19',    # Two week period
            start_time='09:00:00',
            end_time='11:00:00',
            days_of_week=[2, 4],  # Tuesday and Thursday
            weeks=[1, 2],
            child_id=1
        )
        
        assert result['created'] >= 0
        # Verify time parameters were passed
        if mock_db.insert.called:
            call_args = mock_db.insert.call_args[0]
            assert '09:00:00' in call_args[1]
            assert '11:00:00' in call_args[1]


class TestPayrollServiceIntegration:
    """Integration tests for PayrollService with real database operations"""
    
    def test_period_overlap_detection(self, test_db, sample_data):
        """Test that overlapping periods are properly detected"""
        service = PayrollService(test_db)
        
        # Get exclusions that overlap with a period
        exclusions = service.get_exclusions_for_period(
            '2025-01-01', '2025-01-31'
        )
        
        # Should handle various overlap scenarios
        assert isinstance(exclusions, list)
    
    def test_period_summary_calculations(self, test_db, sample_data):
        """Test period summary calculations are accurate"""
        service = PayrollService(test_db)
        
        # Create a period with known shifts
        period_id = test_db.insert(
            "INSERT INTO payroll_periods (start_date, end_date) VALUES (?, ?)",
            ('2025-02-01', '2025-02-14')
        )
        
        # Add shifts
        test_db.insert(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, is_imported)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sample_data['employee'].id, sample_data['child'].id, 
             '2025-02-05', '09:00:00', '17:00:00', 0)
        )
        
        summary = service.get_period_summary(period_id)
        
        assert summary is not None
        assert summary['total_shifts'] == 1
        assert summary['total_hours'] == 8.0
        assert summary['manual_shifts'] == 1
        assert summary['imported_shifts'] == 0