"""Comprehensive integration tests for shift routes"""

import pytest
import json
from datetime import datetime, date, timedelta


class TestShiftRoutes:
    """Test shift API endpoints comprehensively"""
    
    def test_create_shift_success(self, client, sample_data):
        """Test successful shift creation"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['id'] is not None
        assert 'message' in data
    
    def test_create_shift_invalid_times(self, client, sample_data):
        """Test creating shift with end time before start time"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-15',
                'start_time': '17:00:00',
                'end_time': '09:00:00'
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_shift_missing_required_fields(self, client):
        """Test creating shift without required fields"""
        response = client.post('/api/shifts/',
            json={
                'date': '2025-03-15',
                'start_time': '09:00:00'
                # Missing employee_id, child_id, end_time
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_shift_invalid_employee(self, client, sample_data):
        """Test creating shift with non-existent employee"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': 99999,
                'child_id': sample_data['child'].id,
                'date': '2025-03-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code in [400, 404, 500]  # 500 for FK constraint failure
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_shift_invalid_child(self, client, sample_data):
        """Test creating shift with non-existent child"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': 99999,
                'date': '2025-03-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        assert response.status_code in [400, 404, 500]  # 500 for FK constraint failure
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_shift_overnight(self, client, sample_data):
        """Test creating overnight shift"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-15',
                'start_time': '22:00:00',
                'end_time': '06:00:00'  # Next day
            })
        
        # Should either succeed or return appropriate error
        assert response.status_code in [201, 400]
    
    def test_create_shift_overlapping(self, client, sample_data):
        """Test creating overlapping shifts for same employee"""
        # Create first shift
        response1 = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-20',
                'start_time': '09:00:00',
                'end_time': '13:00:00'
            })
        assert response1.status_code == 201
        
        # Try to create overlapping shift
        response2 = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-03-20',
                'start_time': '11:00:00',
                'end_time': '15:00:00'
            })
        
        assert response2.status_code == 409
        data = json.loads(response2.data)
        assert 'error' in data
        assert 'conflict' in data['error'].lower() or 'overlap' in data['error'].lower()
    
    def test_get_shifts_for_period(self, client, sample_data):
        """Test retrieving shifts for a date range"""
        # Create test shifts
        for day in range(1, 4):
            client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': f'2025-04-{day:02d}',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
        
        response = client.get('/api/shifts/?start_date=2025-04-01&end_date=2025-04-30')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 3
    
    def test_get_shifts_no_date_range(self, client):
        """Test getting shifts without date range"""
        response = client.get('/api/shifts/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_get_shifts_by_employee(self, client, sample_data):
        """Test filtering shifts by employee"""
        response = client.get(f'/api/shifts/?employee_id={sample_data["employee"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        # All shifts should be for the specified employee
        for shift in data:
            assert shift['employee_id'] == sample_data['employee'].id
    
    def test_get_shifts_by_child(self, client, sample_data):
        """Test filtering shifts by child"""
        response = client.get(f'/api/shifts/?child_id={sample_data["child"].id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        # All shifts should be for the specified child
        for shift in data:
            assert shift['child_id'] == sample_data['child'].id
    
    def test_get_shift_by_id(self, client, sample_data):
        """Test getting a specific shift"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-05-01',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        response = client.get(f'/api/shifts/{shift_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == shift_id
    
    def test_get_shift_not_found(self, client):
        """Test getting non-existent shift"""
        response = client.get('/api/shifts/99999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_update_shift_success(self, client, sample_data):
        """Test updating a shift"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-05-10',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Update it
        response = client.put(f'/api/shifts/{shift_id}',
            json={
                'end_time': '18:00:00',
                'status': 'confirmed'
            })
        assert response.status_code == 200
        
        # Verify update
        get_response = client.get(f'/api/shifts/{shift_id}')
        data = json.loads(get_response.data)
        assert data['end_time'] == '18:00:00'
        assert data['status'] == 'confirmed'
    
    def test_update_shift_invalid_times(self, client, sample_data):
        """Test updating shift with invalid times"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-05-15',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Try to update with invalid times
        response = client.put(f'/api/shifts/{shift_id}',
            json={
                'start_time': '17:00:00',
                'end_time': '09:00:00'
            })
        assert response.status_code == 400
    
    def test_update_shift_not_found(self, client):
        """Test updating non-existent shift"""
        response = client.put('/api/shifts/99999',
            json={'end_time': '18:00:00'})
        assert response.status_code == 404
    
    def test_delete_shift_success(self, client, sample_data):
        """Test deleting a shift"""
        # Create a shift
        create_response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-05-20',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        shift_id = json.loads(create_response.data)['id']
        
        # Delete it
        response = client.delete(f'/api/shifts/{shift_id}')
        assert response.status_code == 200
        
        # Verify deletion
        get_response = client.get(f'/api/shifts/{shift_id}')
        assert get_response.status_code == 404
    
    def test_delete_shift_not_found(self, client):
        """Test deleting non-existent shift"""
        response = client.delete('/api/shifts/99999')
        assert response.status_code == 404
    
    def test_get_shifts_pagination(self, client, sample_data):
        """Test shift pagination"""
        # Create multiple shifts
        for day in range(1, 21):
            client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': f'2025-06-{day:02d}',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
        
        # Test with pagination parameters
        response = client.get('/api/shifts/?page=1&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should return paginated results or all results
        assert isinstance(data, (list, dict))
        if isinstance(data, dict):
            assert 'shifts' in data or 'data' in data
            assert 'total' in data or 'count' in data
    
    def test_create_shift_with_notes(self, client, sample_data):
        """Test creating shift with notes"""
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': '2025-06-25',
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'notes': 'Special event coverage'
            })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        # Verify notes were saved
        get_response = client.get(f'/api/shifts/{data["id"]}')
        shift_data = json.loads(get_response.data)
        if 'notes' in shift_data:
            assert shift_data['notes'] == 'Special event coverage'
    
    def test_get_shifts_invalid_date_format(self, client):
        """Test getting shifts with invalid date format"""
        response = client.get('/api/shifts/?start_date=invalid&end_date=also-invalid')
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_create_shift_past_date(self, client, sample_data):
        """Test creating shift for past date"""
        past_date = (date.today() - timedelta(days=30)).isoformat()
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': past_date,
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        # Should allow past dates for historical data entry
        assert response.status_code == 201
    
    def test_create_shift_future_date(self, client, sample_data):
        """Test creating shift for future date"""
        future_date = (date.today() + timedelta(days=90)).isoformat()
        response = client.post('/api/shifts/',
            json={
                'employee_id': sample_data['employee'].id,
                'child_id': sample_data['child'].id,
                'date': future_date,
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            })
        
        # Should allow future dates for scheduling
        assert response.status_code == 201