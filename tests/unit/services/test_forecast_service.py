"""Unit tests for ForecastService"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from services.forecast_service import ForecastService


class TestForecastService:
    """Test suite for ForecastService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def mock_services(self):
        """Create mock service instances"""
        return {
            'budget': Mock(),
            'payroll': Mock()
        }
    
    @pytest.fixture
    def service(self, mock_db, mock_services):
        """Create a ForecastService instance with mock dependencies"""
        service = ForecastService(mock_db)
        service.budget_service = mock_services['budget']
        service.payroll_service = mock_services['payroll']
        return service
    
    @pytest.fixture
    def sample_utilization(self):
        """Sample budget utilization data"""
        return {
            'budget_hours': 200.0,
            'actual_hours': 50.0,
            'hours_remaining': 150.0,
            'utilization_percent': 25.0
        }
    
    @pytest.fixture
    def sample_budget(self):
        """Sample budget data"""
        return {
            'id': 1,
            'child_id': 1,
            'period_start': '2025-01-01',
            'period_end': '2025-01-31',
            'budget_hours': 200.0,
            'budget_amount': 5000.00
        }
    
    # Test get_available_hours
    @patch('services.forecast_service.date')
    def test_get_available_hours_with_budget(self, mock_date, service, mock_services, 
                                            mock_db, sample_utilization, sample_budget):
        """Test calculating available hours with budget"""
        mock_date.today.return_value = date(2025, 1, 15)
        mock_services['budget'].get_budget_utilization.return_value = sample_utilization
        mock_services['budget'].get_budget_for_period.return_value = sample_budget
        mock_db.fetchone.return_value = {'total_hours': 20.0}  # Current week usage
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        assert result['child_id'] == 1
        assert result['budget_hours'] == 200.0
        assert result['used_hours'] == 50.0
        assert result['available_hours'] == 150.0
        assert result['days_remaining'] == 17  # Jan 15 to Jan 31
        assert result['average_daily_available'] > 0
        assert result['weekly_available'] > 0
        assert result['weekly_remaining'] > 0
        assert result['utilization_percent'] == 25.0
    
    @patch('services.forecast_service.date')
    def test_get_available_hours_no_utilization(self, mock_date, service, mock_services):
        """Test available hours when no utilization data exists"""
        mock_date.today.return_value = date(2025, 1, 15)
        mock_services['budget'].get_budget_utilization.return_value = None
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        assert result['budget_hours'] == 0
        assert result['used_hours'] == 0
        assert result['available_hours'] == 0
        assert result['average_daily_available'] == 0
        assert result['weekly_available'] == 0
    
    @patch('services.forecast_service.date')
    def test_get_available_hours_no_budget(self, mock_date, service, mock_services,
                                          mock_db, sample_utilization):
        """Test available hours calculation without budget period"""
        mock_date.today.return_value = date(2025, 1, 15)
        mock_services['budget'].get_budget_utilization.return_value = sample_utilization
        mock_services['budget'].get_budget_for_period.return_value = None
        mock_db.fetchone.return_value = None
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        # Should fall back to using period_end for calculations
        assert result['available_hours'] == 150.0
        assert result['days_remaining'] > 0
    
    @patch('services.forecast_service.date')
    def test_get_available_hours_weekly_calculations(self, mock_date, service, 
                                                    mock_services, mock_db,
                                                    sample_utilization, sample_budget):
        """Test weekly hour calculations for payroll period"""
        # Test on a Monday (weekday 0)
        mock_date.today.return_value = date(2025, 1, 13)  # Monday
        mock_services['budget'].get_budget_utilization.return_value = sample_utilization
        mock_services['budget'].get_budget_for_period.return_value = sample_budget
        mock_db.fetchone.return_value = {'total_hours': 16.0}  # Already used this week
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        # Verify payroll week calculation (Thursday to Wednesday)
        call_args = mock_db.fetchone.call_args[0]
        assert 'child_id = ?' in call_args[0]
        # Check the week start is the previous Thursday
        assert '2025-01-09' in call_args[1]  # Previous Thursday
    
    @patch('services.forecast_service.date')
    def test_get_available_hours_on_thursday(self, mock_date, service,
                                            mock_services, mock_db,
                                            sample_utilization, sample_budget):
        """Test weekly calculations when today is Thursday"""
        # Test on a Thursday (weekday 3)
        mock_date.today.return_value = date(2025, 1, 16)  # Thursday
        mock_services['budget'].get_budget_utilization.return_value = sample_utilization
        mock_services['budget'].get_budget_for_period.return_value = sample_budget
        mock_db.fetchone.return_value = {'total_hours': 0}
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        # Week should start today
        call_args = mock_db.fetchone.call_args[0]
        assert '2025-01-16' in call_args[1]  # Today (Thursday)
    
    @patch('services.forecast_service.date')
    def test_get_available_hours_negative_remaining(self, mock_date, service,
                                                   mock_services, mock_db,
                                                   sample_utilization, sample_budget):
        """Test that weekly remaining hours don't go negative"""
        mock_date.today.return_value = date(2025, 1, 15)
        sample_utilization['hours_remaining'] = 10.0  # Low remaining hours
        mock_services['budget'].get_budget_utilization.return_value = sample_utilization
        mock_services['budget'].get_budget_for_period.return_value = sample_budget
        mock_db.fetchone.return_value = {'total_hours': 50.0}  # High week usage
        
        result = service.get_available_hours(1, '2025-01-01', '2025-01-31')
        
        assert result['weekly_remaining'] >= 0  # Should be capped at 0
    
    # Test get_historical_patterns
    @patch('services.forecast_service.date')
    def test_get_historical_patterns(self, mock_date, service, mock_db):
        """Test analyzing historical shift patterns"""
        mock_date.today.return_value = date(2025, 1, 15)
        
        # Mock day-of-week patterns
        patterns = [
            {'day_of_week': 'Monday', 'day_num': 1, 'shift_count': 10, 'avg_hours': 8.0},
            {'day_of_week': 'Wednesday', 'day_num': 3, 'shift_count': 10, 'avg_hours': 6.0},
            {'day_of_week': 'Friday', 'day_num': 5, 'shift_count': 10, 'avg_hours': 4.0}
        ]
        
        # Mock employee distribution
        employees = [
            {'friendly_name': 'John Doe', 'shift_count': 20, 'total_hours': 140.0},
            {'friendly_name': 'Jane Smith', 'shift_count': 10, 'total_hours': 60.0}
        ]
        
        mock_db.fetchall.side_effect = [patterns, employees]
        
        result = service.get_historical_patterns(1, lookback_days=90)
        
        assert result['child_id'] == 1
        assert result['lookback_days'] == 90
        assert len(result['day_patterns']) == 3
        assert result['weekly_average'] > 0  # (140 + 60) / (90/7)
        assert len(result['employee_distribution']) == 2
        assert result['most_common_days'] == ['Monday', 'Wednesday', 'Friday']
    
    @patch('services.forecast_service.date')
    def test_get_historical_patterns_no_data(self, mock_date, service, mock_db):
        """Test historical patterns with no shift data"""
        mock_date.today.return_value = date(2025, 1, 15)
        mock_db.fetchall.side_effect = [[], []]  # No patterns, no employees
        
        result = service.get_historical_patterns(1)
        
        assert result['weekly_average'] == 0
        assert result['day_patterns'] == []
        assert result['employee_distribution'] == []
        assert result['most_common_days'] == []
    
    # Test generate_projection
    @patch('services.forecast_service.date')
    def test_generate_projection_with_patterns(self, mock_date, service, mock_services, mock_db):
        """Test generating projections based on historical patterns"""
        mock_date.today.return_value = date(2025, 1, 15)
        
        # Mock historical patterns
        patterns = {
            'day_patterns': [
                {'day_of_week': 'Monday', 'day_num': 1, 'avg_hours': 8.0},
                {'day_of_week': 'Wednesday', 'day_num': 3, 'avg_hours': 6.0}
            ],
            'weekly_average': 14.0
        }
        
        # Mock available hours
        available = {
            'available_hours': 100.0,
            'weekly_available': 20.0
        }
        
        # Mock budget
        budget = {'budget_hours': 200.0}
        
        with patch.object(service, 'get_historical_patterns', return_value=patterns):
            with patch.object(service, 'get_available_hours', return_value=available):
                mock_services['budget'].get_budget_for_period.return_value = budget
                
                result = service.generate_projection(1, days_ahead=30)
        
        assert result['child_id'] == 1
        assert result['projection_days'] == 30
        assert 'projected_hours' in result
        assert 'confidence_level' in result
        assert 'projected_dates' in result
        assert len(result['projected_dates']) > 0
    
    @patch('services.forecast_service.date')
    def test_generate_projection_no_patterns(self, mock_date, service, mock_services):
        """Test projection when no historical patterns exist"""
        mock_date.today.return_value = date(2025, 1, 15)
        
        patterns = {
            'day_patterns': [],
            'weekly_average': 0
        }
        
        available = {'available_hours': 100.0, 'weekly_available': 20.0}
        
        with patch.object(service, 'get_historical_patterns', return_value=patterns):
            with patch.object(service, 'get_available_hours', return_value=available):
                mock_services['budget'].get_budget_for_period.return_value = None
                
                result = service.generate_projection(1, days_ahead=30)
        
        assert result['projected_hours'] == 0
        assert result['confidence_level'] == 'low'
        assert result['projected_dates'] == []
    
    @patch('services.forecast_service.date')
    def test_generate_projection_confidence_levels(self, mock_date, service, mock_services):
        """Test confidence level calculation in projections"""
        mock_date.today.return_value = date(2025, 1, 15)
        
        # High confidence scenario - consistent patterns
        patterns_high = {
            'day_patterns': [
                {'day_of_week': 'Monday', 'day_num': 1, 'avg_hours': 8.0},
                {'day_of_week': 'Tuesday', 'day_num': 2, 'avg_hours': 8.0},
                {'day_of_week': 'Wednesday', 'day_num': 3, 'avg_hours': 8.0},
                {'day_of_week': 'Thursday', 'day_num': 4, 'avg_hours': 8.0},
                {'day_of_week': 'Friday', 'day_num': 5, 'avg_hours': 8.0}
            ],
            'weekly_average': 40.0
        }
        
        available = {'available_hours': 200.0, 'weekly_available': 40.0}
        budget = {'budget_hours': 200.0}
        
        with patch.object(service, 'get_historical_patterns', return_value=patterns_high):
            with patch.object(service, 'get_available_hours', return_value=available):
                mock_services['budget'].get_budget_for_period.return_value = budget
                
                result = service.generate_projection(1, days_ahead=7)
        
        # Should have high confidence with consistent patterns
        assert result['confidence_level'] in ['high', 'medium']
    
    # Test get_recommendations
    def test_get_recommendations_under_utilized(self, service, mock_services):
        """Test recommendations for under-utilized budget"""
        utilization = {
            'utilization_percent': 30.0,
            'hours_remaining': 140.0,
            'actual_hours': 60.0
        }
        
        available = {
            'days_remaining': 10,
            'weekly_available': 35.0,
            'average_daily_available': 5.0
        }
        
        patterns = {
            'weekly_average': 15.0,
            'most_common_days': ['Monday', 'Wednesday']
        }
        
        mock_services['budget'].get_budget_utilization.return_value = utilization
        
        with patch.object(service, 'get_available_hours', return_value=available):
            with patch.object(service, 'get_historical_patterns', return_value=patterns):
                result = service.get_recommendations(1, '2025-01-01', '2025-01-31')
        
        assert result['status'] == 'under_utilized'
        assert 'increase' in result['recommendations'][0].lower()
        assert result['suggested_weekly_hours'] > patterns['weekly_average']
    
    def test_get_recommendations_on_track(self, service, mock_services):
        """Test recommendations for on-track utilization"""
        utilization = {
            'utilization_percent': 50.0,
            'hours_remaining': 100.0,
            'actual_hours': 100.0
        }
        
        available = {
            'days_remaining': 15,
            'weekly_available': 23.0,
            'average_daily_available': 3.3
        }
        
        patterns = {
            'weekly_average': 23.0,
            'most_common_days': ['Monday', 'Wednesday', 'Friday']
        }
        
        mock_services['budget'].get_budget_utilization.return_value = utilization
        
        with patch.object(service, 'get_available_hours', return_value=available):
            with patch.object(service, 'get_historical_patterns', return_value=patterns):
                result = service.get_recommendations(1, '2025-01-01', '2025-01-31')
        
        assert result['status'] == 'on_track'
        assert 'maintain' in result['recommendations'][0].lower()
    
    def test_get_recommendations_at_risk(self, service, mock_services):
        """Test recommendations for at-risk budget"""
        utilization = {
            'utilization_percent': 85.0,
            'hours_remaining': 30.0,
            'actual_hours': 170.0
        }
        
        available = {
            'days_remaining': 10,
            'weekly_available': 21.0,
            'average_daily_available': 3.0
        }
        
        patterns = {
            'weekly_average': 25.0,
            'most_common_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        }
        
        mock_services['budget'].get_budget_utilization.return_value = utilization
        
        with patch.object(service, 'get_available_hours', return_value=available):
            with patch.object(service, 'get_historical_patterns', return_value=patterns):
                result = service.get_recommendations(1, '2025-01-01', '2025-01-31')
        
        assert result['status'] == 'at_risk'
        assert 'reduce' in result['recommendations'][0].lower() or 'limit' in result['recommendations'][0].lower()
        assert result['suggested_weekly_hours'] < patterns['weekly_average']
    
    def test_get_recommendations_no_budget(self, service, mock_services):
        """Test recommendations when no budget exists"""
        mock_services['budget'].get_budget_utilization.return_value = None
        
        result = service.get_recommendations(1, '2025-01-01', '2025-01-31')
        
        assert result['status'] == 'no_budget'
        assert 'budget' in result['recommendations'][0].lower()
        assert result['suggested_weekly_hours'] == 0


class TestForecastServiceIntegration:
    """Integration tests for ForecastService"""
    
    def test_available_hours_calculation(self, test_db, sample_data):
        """Test complete available hours calculation with real data"""
        from services.budget_service import BudgetService
        
        service = ForecastService(test_db)
        budget_service = BudgetService(test_db)
        
        # Create a budget
        budget_service.create_child_budget(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28',
            budget_hours=160.0
        )
        
        # Create some shifts
        for i in range(5):
            test_db.insert(
                """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                   VALUES (?, ?, ?, ?, ?)""",
                (sample_data['employee'].id, sample_data['child'].id,
                 f'2025-02-{i+1:02d}', '09:00:00', '17:00:00')
            )
        
        # Get available hours
        result = service.get_available_hours(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28'
        )
        
        assert result['budget_hours'] == 160.0
        assert result['used_hours'] == 40.0  # 5 days * 8 hours
        assert result['available_hours'] == 120.0
        assert result['utilization_percent'] == 25.0
    
    def test_historical_patterns_analysis(self, test_db, sample_data):
        """Test historical pattern analysis with real data"""
        service = ForecastService(test_db)
        
        # Create shifts with patterns (Mondays and Wednesdays)
        dates = [
            '2025-01-06',  # Monday
            '2025-01-08',  # Wednesday
            '2025-01-13',  # Monday
            '2025-01-15',  # Wednesday
            '2025-01-20',  # Monday
            '2025-01-22',  # Wednesday
        ]
        
        for date_str in dates:
            test_db.insert(
                """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                   VALUES (?, ?, ?, ?, ?)""",
                (sample_data['employee'].id, sample_data['child'].id,
                 date_str, '09:00:00', '17:00:00')
            )
        
        result = service.get_historical_patterns(sample_data['child'].id, lookback_days=30)
        
        assert len(result['day_patterns']) > 0
        assert result['weekly_average'] > 0
        # Should identify Monday and Wednesday as common days
        assert 'Monday' in result['most_common_days']
        assert 'Wednesday' in result['most_common_days']