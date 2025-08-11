"""Integration tests for API routes"""

import pytest
import json
from datetime import datetime, date


class TestEmployeeRoutes:
    """Test employee API endpoints"""
    
    def test_get_all_employees(self, client, sample_data):
        """Test GET /api/employees/"""
        response = client.get('/api/employees/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]['id'] == sample_data['employee'].id
    
    def test_create_employee(self, client):
        """Test POST /api/employees"""
        response = client.post('/api/employees/', 
            json={
                'friendly_name': 'Test Employee',
                'system_name': 'test.employee'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
        assert data['message'] == 'Employee created'
    
    def test_update_employee(self, client, sample_data):
        """Test PUT /api/employees/<id>"""
        response = client.put(f'/api/employees/{sample_data["employee"].id}',
            json={'friendly_name': 'Updated Name'})
        assert response.status_code == 200
        
        # Verify update
        response = client.get(f'/api/employees/{sample_data["employee"].id}')
        data = json.loads(response.data)
        assert data['friendly_name'] == 'Updated Name'
    
    def test_deactivate_employee(self, client, sample_data):
        """Test DELETE /api/employees/<id>"""
        response = client.delete(f'/api/employees/{sample_data["employee"].id}')
        assert response.status_code == 200
        
        # Verify deactivation
        response = client.get('/api/employees/')
        data = json.loads(response.data)
        employee = next((e for e in data if e['id'] == sample_data['employee'].id), None)
        assert employee['active'] == 0
    
    def test_get_employee_not_found(self, client):
        """Test GET /api/employees/<id> with invalid ID"""
        response = client.get('/api/employees/999999')
        assert response.status_code == 404


class TestChildrenRoutes:
    """Test children API endpoints"""
    
    def test_get_all_children(self, client, sample_data):
        """Test GET /api/children"""
        response = client.get('/api/children/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_create_child(self, client):
        """Test POST /api/children"""
        response = client.post('/api/children/',
            json={
                'name': 'Test Child',
                'code': 'TC001'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
    
    def test_create_child_duplicate_code(self, client, sample_data):
        """Test creating child with duplicate code"""
        response = client.post('/api/children/',
            json={
                'name': 'Another Child',
                'code': sample_data['child'].code
            })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'already exists' in data['error']


class TestShiftRoutes:
    """Test shift API endpoints"""
    
    def test_create_shift(self, client, sample_data):
        """Test POST /api/shifts"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-01',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
    
    def test_create_shift_invalid_times(self, client, sample_data):
        """Test creating shift with invalid times"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-01',
                'start_time': '17:00:00',
                'end_time': '09:00:00'  # End before start
            })
        assert response.status_code == 400
    
    def test_get_shifts_for_period(self, client, sample_data):
        """Test GET /api/shifts with date range"""
        # Create a shift first
        client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        response = client.get('/api/shifts/?start_date=2025-03-01&end_date=2025-03-31')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0
        assert data[0]['date'] == '2025-03-15'
    
    def test_update_shift(self, client, sample_data):
        """Test PUT /api/shifts/<id>"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-01',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Update it
        response = client.put(f'/api/shifts/{shift_id}',
            json={'end_time': '18:00:00'})
        assert response.status_code == 200
        
        # Verify update
        response = client.get(f'/api/shifts/{shift_id}')
        data = json.loads(response.data)
        assert data['end_time'] == '18:00:00'
    
    def test_delete_shift(self, client, sample_data):
        """Test DELETE /api/shifts/<id>"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-01',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Delete it
        response = client.delete(f'/api/shifts/{shift_id}')
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f'/api/shifts/{shift_id}')
        assert response.status_code == 404


class TestPayrollRoutes:
    """Test payroll API endpoints"""
    
    def test_get_current_period(self, client):
        """Test GET /api/payroll/periods/current"""
        # First configure payroll periods with current date
        from datetime import date, timedelta
        today = date.today()
        # Find the most recent Thursday
        days_since_thursday = (today.weekday() - 3) % 7
        if days_since_thursday == 0:
            days_since_thursday = 7
        last_thursday = today - timedelta(days=days_since_thursday)
        
        config_response = client.post('/api/payroll/periods/configure',
            json={'anchor_date': last_thursday.isoformat()})
        assert config_response.status_code == 200
        
        # Now get current period
        response = client.get('/api/payroll/periods/current')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'start_date' in data
        assert 'end_date' in data
    
    def test_create_exclusion_period(self, client, sample_data):
        """Test POST /api/payroll/exclusions"""
        response = client.post('/api/payroll/exclusions',
            json={
                'name': 'Test Exclusion',
                'start_date': '2025-04-01',
                'end_date': '2025-04-07',
                'employee_id': sample_data['employee'].id,
                'reason': 'Vacation'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
    
    def test_create_exclusion_xor_validation(self, client, sample_data):
        """Test exclusion XOR validation (employee OR child, not both)"""
        response = client.post('/api/payroll/exclusions',
            json={
                'name': 'Invalid Exclusion',
                'start_date': '2025-04-01',
                'end_date': '2025-04-07',
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,  # Both IDs provided
                'reason': 'Invalid'
            })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'employee or a child' in data['error'].lower()
    
    def test_get_period_summary(self, client, sample_data):
        """Test GET /api/payroll/periods/<id>/summary"""
        # First configure payroll periods
        from datetime import date, timedelta
        today = date.today()
        days_since_thursday = (today.weekday() - 3) % 7
        if days_since_thursday == 0:
            days_since_thursday = 7
        last_thursday = today - timedelta(days=days_since_thursday)
        
        config_response = client.post('/api/payroll/periods/configure',
            json={'anchor_date': last_thursday.isoformat()})
        assert config_response.status_code == 200
        
        # Get current period
        period_response = client.get('/api/payroll/periods/current')
        period = json.loads(period_response.data)
        
        response = client.get(f'/api/payroll/periods/{period["id"]}/summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_hours' in data
        assert 'total_shifts' in data


class TestImportExportRoutes:
    """Test import/export API endpoints"""
    
    def test_csv_import(self, client, sample_data):
        """Test POST /api/imports/csv"""
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
03/01/2025,{sample_data['child'].name} ({sample_data['child'].code}),{sample_data['employee'].friendly_name},09:00 AM,05:00 PM"""
        
        from io import BytesIO
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'test.csv', 'text/csv')},
            content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'imported' in data
        assert data['imported'] >= 0
    
    def test_csv_export(self, client):
        """Test POST /api/export/csv"""
        response = client.post('/api/export/csv',
            json={
                'start_date': '2025-03-01',
                'end_date': '2025-03-31'
            })
        assert response.status_code == 200
        assert 'text/csv' in response.content_type
    
    def test_json_export(self, client):
        """Test POST /api/export/json"""
        response = client.post('/api/export/json',
            json={
                'start_date': '2025-03-01',
                'end_date': '2025-03-31'
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'shifts' in data
        assert 'summary' in data
        assert 'export_date' in data


class TestBudgetRoutes:
    """Test budget API endpoints"""
    
    def test_create_child_budget(self, client, sample_data):
        """Test POST /api/budget/children"""
        response = client.post('/api/budget/children',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30',
                'budget_amount': 5000.00,
                'budget_hours': 200.0,
                'notes': 'April budget'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'Budget created successfully'
    
    def test_get_child_budgets(self, client):
        """Test GET /api/budget/children"""
        response = client.get('/api/budget/children')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_create_employee_rate(self, client, sample_data):
        """Test POST /api/budget/rates"""
        response = client.post('/api/budget/rates',
            json={
                'employee_id': sample_data['employee'].id,
                'hourly_rate': 25.00,
                'effective_date': '2025-04-01'
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
    
    def test_get_utilization(self, client, sample_data):
        """Test GET /api/budget/utilization"""
        # First create a budget for the child
        budget_response = client.post('/api/budget/children',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30',
                'budget_amount': 5000.00,
                'budget_hours': 200
            })
        assert budget_response.status_code == 201
        
        # Now test utilization
        response = client.get('/api/budget/utilization',
            query_string={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30'
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'budget' in data
        assert 'spent' in data
        assert 'utilization_percentage' in data


class TestForecastRoutes:
    """Test forecast API endpoints"""
    
    def test_get_available_hours(self, client, sample_data):
        """Test GET /api/forecast/available-hours"""
        response = client.get('/api/forecast/available-hours',
            query_string={
                'child_id': sample_data['child'].id,
                'period_start': '2025-04-01',
                'period_end': '2025-04-30'
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'available_hours' in data
        assert 'budget_hours' in data
        assert 'used_hours' in data
    
    def test_get_patterns(self, client, sample_data):
        """Test GET /api/forecast/patterns"""
        response = client.get('/api/forecast/patterns',
            query_string={
                'child_id': sample_data['child'].id,
                'lookback_days': 90
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'analysis_period' in data
        assert 'total_hours_analyzed' in data
    
    def test_generate_projection(self, client, sample_data):
        """Test GET /api/forecast/projections"""
        response = client.get('/api/forecast/projections',
            query_string={
                'child_id': sample_data['child'].id,
                'days_ahead': 30
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'projected_hours' in data
        assert 'confidence' in data
        assert 'based_on' in data


class TestConfigRoutes:
    """Test configuration API endpoints"""
    
    def test_get_hour_limits(self, client):
        """Test GET /api/config/hour-limits"""
        response = client.get('/api/config/hour-limits')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_create_hour_limit(self, client, sample_data):
        """Test POST /api/config/hour-limits"""
        response = client.post('/api/config/hour-limits',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'max_hours_per_week': 20.0,
                'alert_threshold': 18.0
            })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
    
    def test_get_app_settings(self, client):
        """Test GET /api/config/settings"""
        response = client.get('/api/config/settings')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)
    
    def test_update_app_settings(self, client):
        """Test PUT /api/config/settings"""
        response = client.put('/api/config/settings',
            json={
                'timezone': 'America/New_York',
                'test_setting': 'test_value'
            })
        assert response.status_code == 200
        
        # Verify update
        response = client.get('/api/config/settings')
        data = json.loads(response.data)
        assert data.get('test_setting') == 'test_value'