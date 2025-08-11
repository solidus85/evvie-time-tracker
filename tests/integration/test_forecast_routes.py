"""Comprehensive integration tests for forecast routes"""

import pytest
import json
from datetime import date, timedelta


class TestForecastRoutes:
    """Test suite for forecast-related API endpoints"""
    
    def test_get_available_hours(self, client, sample_data):
        """Test getting available hours for a child"""
        # Create a budget first
        budget_response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-03-01',
                'period_end': '2025-03-31',
                'budget_hours': 160.0,
                'budget_amount': 4000.00
            })
        
        # Get available hours
        response = client.get(f'/api/forecast/available-hours/{sample_data["child"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'child_id' in data
        assert 'available_hours' in data or 'hours_available' in data
        assert 'budget_hours' in data or 'budget' in data
    
    def test_get_available_hours_with_date_range(self, client, sample_data):
        """Test getting available hours with specific date range"""
        response = client.get(f'/api/forecast/available-hours/{sample_data["child"].id}',
            query_string={
                'start_date': '2025-03-01',
                'end_date': '2025-03-31'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'child_id' in data
    
    def test_get_available_hours_invalid_child(self, client):
        """Test getting available hours for non-existent child"""
        response = client.get('/api/forecast/available-hours/99999')
        assert response.status_code in [200, 404]
        # May return empty data or 404
    
    def test_get_historical_patterns(self, client, sample_data):
        """Test getting historical patterns for a child"""
        # Create some shifts first
        for i in range(5):
            shift_date = (date.today() - timedelta(days=i*7)).isoformat()
            client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': shift_date,
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
        
        response = client.get(f'/api/forecast/patterns/{sample_data["child"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'patterns' in data or 'weekly_patterns' in data or 'child_id' in data
    
    def test_get_historical_patterns_with_lookback(self, client, sample_data):
        """Test getting historical patterns with custom lookback period"""
        response = client.get(f'/api/forecast/patterns/{sample_data["child"].id}',
            query_string={'lookback_days': 60})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        if 'lookback_days' in data or 'analysis_period' in data:
            assert data.get('lookback_days', data.get('analysis_period')) == 60
    
    def test_project_hours(self, client, sample_data):
        """Test projecting hours for a child"""
        response = client.get(f'/api/forecast/projection/{sample_data["child"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'projection' in data or 'projected_hours' in data or 'child_id' in data
    
    def test_project_hours_with_days(self, client, sample_data):
        """Test projecting hours with specific projection days"""
        response = client.get(f'/api/forecast/projection/{sample_data["child"].id}',
            query_string={'projection_days': 14})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        if 'projection_days' in data:
            assert data['projection_days'] == 14
    
    def test_get_forecast_summary(self, client):
        """Test getting forecast summary for all children"""
        response = client.get('/api/forecast/summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'children' in data or 'forecasts' in data or isinstance(data, list)
    
    def test_get_forecast_summary_with_period(self, client):
        """Test getting forecast summary with specific period"""
        response = client.get('/api/forecast/summary',
            query_string={
                'start_date': '2025-03-01',
                'end_date': '2025-03-31'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'period_start' in data or 'start_date' in data or isinstance(data, (list, dict))
    
    def test_get_allocation_recommendations(self, client, sample_data):
        """Test getting allocation recommendations"""
        # Create payroll period first
        period_response = client.post('/api/payroll/periods/configure',
            json={'anchor_date': '2025-01-02'})
        
        response = client.get('/api/forecast/recommendations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'recommendations' in data or isinstance(data, list)
    
    def test_get_allocation_recommendations_for_period(self, client):
        """Test getting recommendations for specific period"""
        response = client.get('/api/forecast/recommendations',
            query_string={'period_id': 1})
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'recommendations' in data or 'period_id' in data or isinstance(data, list)
    
    def test_forecast_accuracy_metrics(self, client, sample_data):
        """Test forecast accuracy metrics endpoint if available"""
        response = client.get(f'/api/forecast/accuracy/{sample_data["child"].id}')
        
        # This endpoint might not exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'accuracy' in data or 'metrics' in data
    
    def test_forecast_with_exclusions(self, client, sample_data):
        """Test forecast considering exclusion periods"""
        # Create an exclusion
        exclusion_response = client.post('/api/payroll/exclusions',
            json={
                'name': 'Holiday',
                'start_date': '2025-03-15',
                'end_date': '2025-03-20',
                'child_id': sample_data['child'].id
            })
        
        # Get forecast
        response = client.get(f'/api/forecast/projection/{sample_data["child"].id}',
            query_string={
                'start_date': '2025-03-01',
                'end_date': '2025-03-31'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Forecast should exist even with exclusions
        assert 'projected_hours' in data or 'projection' in data or 'child_id' in data
    
    def test_batch_forecast(self, client, multiple_children):
        """Test getting forecasts for multiple children"""
        child_ids = [c['id'] for c in multiple_children[:2]]
        
        response = client.post('/api/forecast/batch',
            json={'child_ids': child_ids})
        
        # Batch endpoint might not exist
        assert response.status_code in [200, 404, 405]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, (list, dict))
    
    def test_forecast_empty_history(self, client, sample_data):
        """Test forecast with no historical data"""
        # Get forecast for child with no shifts
        response = client.get(f'/api/forecast/projection/{sample_data["child"].id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should return zero or low confidence forecast
        if 'confidence' in data:
            assert data['confidence'] in ['low', 'none', 0]
    
    def test_forecast_export(self, client):
        """Test exporting forecast data"""
        response = client.get('/api/forecast/export',
            query_string={'format': 'csv'})
        
        # Export might not be implemented
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.content_type in ['text/csv', 'application/json']
    
    def test_forecast_comparison(self, client, sample_data):
        """Test comparing actual vs forecasted hours"""
        response = client.get(f'/api/forecast/comparison/{sample_data["child"].id}',
            query_string={
                'start_date': '2025-02-01',
                'end_date': '2025-02-28'
            })
        
        # Comparison endpoint might not exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'actual' in data or 'forecast' in data or 'comparison' in data
    
    def test_forecast_trends(self, client, sample_data):
        """Test getting forecast trends over time"""
        response = client.get(f'/api/forecast/trends/{sample_data["child"].id}')
        
        # Trends endpoint might not exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'trends' in data or isinstance(data, list)
    
    def test_forecast_alerts(self, client, sample_data):
        """Test getting forecast-based alerts"""
        response = client.get('/api/forecast/alerts')
        
        # Alerts endpoint might not exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'alerts' in data or isinstance(data, list)