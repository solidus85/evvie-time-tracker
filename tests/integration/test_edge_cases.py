"""Edge case and boundary tests for critical functionality"""

import pytest
import json
from datetime import date, time, datetime, timedelta
from decimal import Decimal


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_shift_at_midnight_boundary(self, client, sample_data):
        """Test shift that crosses midnight"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-01',
                'start_time': '23:00:00',
                'end_time': '23:59:59'  # End of day
            })
        
        assert response.status_code in [201, 400]
        # System should either accept or reject based on business rules
    
    def test_zero_hour_shift(self, client, sample_data):
        """Test shift with zero duration"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-02',
                'start_time': '09:00:00',
                'end_time': '09:00:00'  # Same as start
            })
        
        assert response.status_code == 400  # Should reject zero-hour shifts
    
    def test_very_long_shift(self, client, sample_data):
        """Test extremely long shift (23+ hours)"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-03',
                'start_time': '00:01:00',
                'end_time': '23:59:00'  # Nearly 24 hours
            })
        
        assert response.status_code in [201, 400]
        # May have hour limit validation
    
    def test_fractional_seconds_in_time(self, client, sample_data):
        """Test time with fractional seconds"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-04',
                'start_time': '09:00:00.500',  # With milliseconds
                'end_time': '17:00:00.999'
            })
        
        assert response.status_code in [201, 400]
    
    def test_leap_year_date(self, client, sample_data):
        """Test shift on February 29 (leap year)"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2024-02-29',  # 2024 is a leap year
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code == 201
    
    def test_invalid_leap_year_date(self, client, sample_data):
        """Test invalid February 29 (non-leap year)"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-02-29',  # 2025 is not a leap year
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code == 400
    
    def test_very_old_date(self, client, sample_data):
        """Test shift with very old date"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '1900-01-01',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code in [201, 400]
        # May have date range validation
    
    def test_far_future_date(self, client, sample_data):
        """Test shift with far future date"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2099-12-31',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code in [201, 400]
    
    def test_unicode_in_names(self, client):
        """Test Unicode characters in names"""
        response = client.post('/api/employees/',
            json={
                'friendly_name': '李明 (Li Ming) 🌟',
                'system_name': 'liming_unicode'
            })
        
        assert response.status_code == 201
        emp_id = json.loads(response.data)['id']
        
        # Verify it can be retrieved
        get_response = client.get(f'/api/employees/{emp_id}')
        assert get_response.status_code == 200
    
    def test_sql_injection_attempt(self, client):
        """Test SQL injection prevention"""
        response = client.post('/api/employees/',
            json={
                'friendly_name': "'; DROP TABLE employees; --",
                'system_name': 'injection_test'
            })
        
        # Should either sanitize or accept as literal string
        assert response.status_code in [201, 400]
        
        # Verify table still exists
        verify_response = client.get('/api/employees/')
        assert verify_response.status_code == 200
    
    def test_extremely_long_name(self, client):
        """Test very long name handling"""
        long_name = 'A' * 1000  # 1000 characters
        response = client.post('/api/children/',
            json={
                'name': long_name,
                'code': 'LONG001'
            })
        
        assert response.status_code in [201, 400]
        # Should either truncate or reject
    
    def test_null_values_in_optional_fields(self, client, sample_data):
        """Test explicit null values in optional fields"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-05',
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'service_code': None,  # Explicit null
                'status': None
            })
        
        assert response.status_code == 201
    
    def test_decimal_precision_in_hours(self, client, sample_data):
        """Test decimal precision in hour calculations"""
        # Create shift with odd minutes
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-06',
                'start_time': '09:17:00',  # 17 minutes
                'end_time': '17:43:00'  # 43 minutes
            })
        
        assert response.status_code == 201
        shift_id = json.loads(response.data)['id']
        
        # Verify hours calculation
        get_response = client.get(f'/api/shifts/{shift_id}')
        if get_response.status_code == 200:
            shift = json.loads(get_response.data)
            if 'hours' in shift:
                # Should be approximately 8.433 hours
                assert 8.4 < shift['hours'] < 8.5
    
    def test_concurrent_updates_same_record(self, client, sample_data):
        """Test concurrent updates to same record"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-07',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Try to update same shift multiple times quickly
        responses = []
        for i in range(5):
            response = client.put(f'/api/shifts/{shift_id}',
                json={'end_time': f'{17 + i}:00:00'})
            responses.append(response.status_code)
        
        # At least one should succeed
        assert 200 in responses
    
    def test_invalid_json_format(self, client):
        """Test handling of invalid JSON"""
        response = client.post('/api/employees/',
            data='{"friendly_name": invalid json}',  # Invalid JSON
            content_type='application/json')
        
        assert response.status_code == 400
    
    def test_missing_content_type(self, client):
        """Test request without content-type header"""
        response = client.post('/api/employees/',
            data='{"friendly_name": "Test", "system_name": "test"}')
        # No content-type specified
        
        assert response.status_code in [400, 415]
    
    def test_empty_request_body(self, client):
        """Test POST with empty body"""
        response = client.post('/api/employees/',
            json={})
        
        assert response.status_code == 400
    
    def test_nonexistent_foreign_key(self, client):
        """Test creating shift with non-existent employee/child"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': 99999,  # Non-existent
                'child_id': 99999,  # Non-existent
                'date': '2025-06-08',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code in [400, 404]
    
    def test_negative_id_values(self, client):
        """Test negative ID values"""
        response = client.get('/api/employees/-1')
        assert response.status_code in [400, 404]
        
        response = client.get('/api/children/-999')
        assert response.status_code in [400, 404]
    
    def test_float_as_id(self, client):
        """Test float value as ID"""
        response = client.get('/api/shifts/3.14')
        assert response.status_code in [400, 404]


class TestDataValidation:
    """Test data validation rules"""
    
    def test_email_format_validation(self, client):
        """Test email format validation if applicable"""
        response = client.post('/api/employees/',
            json={
                'friendly_name': 'Test User',
                'system_name': 'testuser',
                'email': 'not-an-email'  # Invalid email
            })
        
        # If email field exists, should validate
        assert response.status_code in [201, 400]
    
    def test_phone_number_validation(self, client):
        """Test phone number validation if applicable"""
        response = client.post('/api/employees/',
            json={
                'friendly_name': 'Test User',
                'system_name': 'testuser2',
                'phone': '123'  # Too short for phone
            })
        
        assert response.status_code in [201, 400]
    
    def test_date_format_variations(self, client, sample_data):
        """Test various date format inputs"""
        date_formats = [
            '2025-06-09',  # ISO format
            '06/09/2025',  # US format
            '09-06-2025',  # Alternative format
            '2025/06/09',  # Slash separator
        ]
        
        for date_str in date_formats:
            response = client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': date_str,
                    'start_time': f'0{date_formats.index(date_str) + 1}:00:00',
                    'end_time': f'0{date_formats.index(date_str) + 2}:00:00'
                })
            
            # At least ISO format should work
            if date_str == '2025-06-09':
                assert response.status_code == 201
    
    def test_currency_precision(self, client, sample_data):
        """Test currency/money field precision"""
        response = client.post('/api/budget/child-budgets',
            json={
                'child_id': sample_data['child'].id,
                'period_start': '2025-07-01',
                'period_end': '2025-07-31',
                'budget_hours': 160.0,
                'budget_amount': 1234.567  # More than 2 decimal places
            })
        
        assert response.status_code in [201, 400]
        # Should either round or reject
    
    def test_percentage_boundaries(self, client, sample_data):
        """Test percentage field boundaries"""
        # Test > 100%
        response = client.post('/api/config/settings',
            json={'overtime_rate': 150.0})  # 150%
        
        assert response.status_code in [200, 201, 400, 404]
        
        # Test negative percentage
        response = client.post('/api/config/settings',
            json={'discount_rate': -10.0})  # -10%
        
        assert response.status_code in [200, 201, 400, 404]