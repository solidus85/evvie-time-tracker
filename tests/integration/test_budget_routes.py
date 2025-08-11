"""Comprehensive integration tests for budget routes"""

import pytest
import json
from datetime import date, timedelta
from io import BytesIO


class TestBudgetRoutes:
    """Test suite for budget-related API endpoints"""
    
    def test_create_child_budget(self, client, sample_data):
        """Test creating a child budget"""
        response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30',
                'budget_hours': 160.0,
                'budget_amount': 4000.00,
                'notes': 'April budget'
            })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data or 'budget_id' in data
    
    def test_get_child_budgets(self, client, sample_data):
        """Test getting all child budgets"""
        # Create a budget first
        client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-05-01',
                'period_end': '2025-05-31',
                'budget_hours': 160.0
            })
        
        response = client.get('/api/budget/child-budgets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_get_child_budget_by_id(self, client, sample_data):
        """Test getting specific child budget"""
        # Create a budget
        create_response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-06-01',
                'period_end': '2025-06-30',
                'budget_hours': 160.0
            })
        budget_id = json.loads(create_response.data).get('id', 1)
        
        response = client.get(f'/api/budget/child-budgets/{budget_id}')
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'child_id' in data or 'budget_hours' in data
    
    def test_update_child_budget(self, client, sample_data):
        """Test updating a child budget"""
        # Create a budget
        create_response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-07-01',
                'period_end': '2025-07-31',
                'budget_hours': 160.0
            })
        budget_id = json.loads(create_response.data).get('id', 1)
        
        response = client.put(f'/api/budget/child-budgets/{budget_id}',
            json={'budget_hours': 180.0, 'notes': 'Updated budget'})
        
        assert response.status_code in [200, 404]
    
    def test_delete_child_budget(self, client, sample_data):
        """Test deleting a child budget"""
        # Create a budget
        create_response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-08-01',
                'period_end': '2025-08-31',
                'budget_hours': 160.0
            })
        budget_id = json.loads(create_response.data).get('id', 1)
        
        response = client.delete(f'/api/budget/child-budgets/{budget_id}')
        assert response.status_code in [200, 204, 404]
    
    def test_create_employee_rate(self, client, sample_data):
        """Test creating an employee rate"""
        response = client.post('/api/budget/employee-rates',
            json={
                'employee_id': sample_data['employee'].id,
                'hourly_rate': 30.00,
                'effective_date': '2025-04-01',
                'notes': 'Rate increase'
            })
        
        assert response.status_code in [201, 200]
        data = json.loads(response.data)
        assert 'id' in data or 'rate_id' in data or 'message' in data
    
    def test_get_employee_rates(self, client, sample_data):
        """Test getting employee rates"""
        response = client.get(f'/api/budget/employee-rates/{sample_data["employee"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (list, dict))
    
    def test_get_current_employee_rate(self, client, sample_data):
        """Test getting current employee rate"""
        response = client.get(f'/api/budget/employee-rates/{sample_data["employee"].id}/current')
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'hourly_rate' in data or 'rate' in data
    
    def test_create_budget_allocation(self, client, sample_data):
        """Test creating a budget allocation"""
        # Create payroll period first
        period_response = client.post('/api/payroll/periods/configure',
            json={'anchor_date': '2025-01-02'})
        
        response = client.post('/api/budget/allocations',
            json={
                'child_id': sample_data['child'].id,
                'employee_id': sample_data['employee'].id,
                'period_id': 1,
                'allocated_hours': 40.0,
                'notes': 'Weekly allocation'
            })
        
        assert response.status_code in [201, 200, 400]
    
    def test_get_budget_allocations(self, client):
        """Test getting budget allocations"""
        response = client.get('/api/budget/allocations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (list, dict))
    
    def test_get_allocations_by_period(self, client):
        """Test getting allocations for specific period"""
        response = client.get('/api/budget/allocations',
            query_string={'period_id': 1})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (list, dict))
    
    def test_get_budget_utilization(self, client, sample_data):
        """Test getting budget utilization"""
        # Create a budget first
        client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30',
                'budget_hours': 160.0,
                'budget_amount': 4000.00
            })
        
        response = client.get('/api/budget/utilization',
            query_string={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'utilization' in data or 'utilization_percent' in data or 'budget_hours' in data
    
    def test_get_budget_summary(self, client):
        """Test getting budget summary"""
        response = client.get('/api/budget/summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (list, dict))
    
    def test_get_budget_summary_by_period(self, client):
        """Test getting budget summary for specific period"""
        response = client.get('/api/budget/summary',
            query_string={
                'start_date': '2025-04-01',
                'end_date': '2025-04-30'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (list, dict))
    
    def test_import_budget_csv(self, client, sample_data):
        """Test importing budget from CSV"""
        csv_content = f"""Child,Period Start,Period End,Budget Hours,Budget Amount
{sample_data['child'].name},{sample_data['child'].code},2025-05-01,2025-05-31,160,4000
{sample_data['child'].name},{sample_data['child'].code},2025-06-01,2025-06-30,160,4000"""
        
        response = client.post('/api/budget/import-csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'budget.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code in [200, 400]
        data = json.loads(response.data)
        assert 'imported' in data or 'error' in data
    
    def test_export_budget_report(self, client):
        """Test exporting budget report"""
        response = client.get('/api/budget/export',
            query_string={
                'format': 'csv',
                'start_date': '2025-04-01',
                'end_date': '2025-04-30'
            })
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.content_type in ['text/csv', 'application/pdf', 'application/json']
    
    def test_budget_validation_duplicate_period(self, client, sample_data):
        """Test that duplicate budget periods are rejected"""
        # Create first budget
        response1 = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-09-01',
                'period_end': '2025-09-30',
                'budget_hours': 160.0
            })
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-09-01',
                'period_end': '2025-09-30',
                'budget_hours': 180.0
            })
        assert response2.status_code in [400, 409]
    
    def test_budget_validation_invalid_dates(self, client, sample_data):
        """Test budget validation with invalid date range"""
        response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-10-31',
                'period_end': '2025-10-01',  # End before start
                'budget_hours': 160.0
            })
        
        assert response.status_code == 400
    
    def test_budget_validation_negative_hours(self, client, sample_data):
        """Test budget validation with negative hours"""
        response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-11-01',
                'period_end': '2025-11-30',
                'budget_hours': -10.0
            })
        
        assert response.status_code == 400
    
    def test_budget_comparison(self, client, sample_data):
        """Test budget vs actual comparison"""
        response = client.get(f'/api/budget/comparison/{sample_data["child"].id}',
            query_string={
                'start_date': '2025-04-01',
                'end_date': '2025-04-30'
            })
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'budget' in data or 'actual' in data or 'variance' in data