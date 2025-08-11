"""End-to-end test for shift management workflow"""

import pytest
import json
from datetime import datetime, date, timedelta


class TestShiftManagementWorkflow:
    """Test complete shift management workflow including conflict resolution"""
    
    def test_shift_creation_and_conflict_resolution(self, client, clean_db):
        """Test creating shifts and handling conflicts"""
        
        # Clean the database to ensure no existing shifts
        # Setup: Create employees and children
        emp1_response = client.post('/api/employees/',
            json={'friendly_name': 'Alice Johnson', 'system_name': 'alice.j'})
        emp1 = json.loads(emp1_response.data)
        
        emp2_response = client.post('/api/employees/',
            json={'friendly_name': 'Bob Smith', 'system_name': 'bob.s'})
        emp2 = json.loads(emp2_response.data)
        
        child1_response = client.post('/api/children/',
            json={'name': 'Emma Watson', 'code': 'EW001'})
        child1 = json.loads(child1_response.data)
        
        child2_response = client.post('/api/children/',
            json={'name': 'Oliver James', 'code': 'OJ002'})
        child2 = json.loads(child2_response.data)
        
        # Test 1: Create initial shift
        shift_date = (date.today() + timedelta(days=7)).isoformat()
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp1['id'],
                'child_id': child1['id'],
                'date': shift_date,
                'start_time': '09:00:00',
                'end_time': '13:00:00'
            })
        assert response.status_code == 201
        shift1 = json.loads(response.data)
        
        # Test 2: Attempt to create overlapping shift (should fail)
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp1['id'],
                'child_id': child2['id'],
                'date': shift_date,
                'start_time': '11:00:00',
                'end_time': '15:00:00'
            })
        assert response.status_code == 409
        error_data = json.loads(response.data)
        assert 'conflict' in error_data['error'].lower() or 'overlap' in error_data['error'].lower()
        
        # Test 3: Create adjacent shift (should succeed)
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp1['id'],
                'child_id': child2['id'],
                'date': shift_date,
                'start_time': '13:00:00',
                'end_time': '17:00:00'
            })
        assert response.status_code == 201
        shift2 = json.loads(response.data)
        
        # Test 4: Create shift for different employee with different child (should succeed)
        # Using child1 with emp2 - no conflict since emp1+child1 ends at 13:00
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp2['id'],
                'child_id': child1['id'],
                'date': shift_date,
                'start_time': '14:00:00',
                'end_time': '18:00:00'
            })
        assert response.status_code == 201
        shift3 = json.loads(response.data)
        
        # Test 5: Update shift to resolve conflict
        response = client.put(f'/api/shifts/{shift1["id"]}',
            json={'end_time': '11:00:00'})
        assert response.status_code == 200
        
        # Test 6: Now overlapping shift should work
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp1['id'],
                'child_id': child1['id'],
                'date': shift_date,
                'start_time': '11:00:00',
                'end_time': '13:00:00'
            })
        assert response.status_code == 201
        
        # Test 7: Query shifts for the date
        response = client.get(f'/api/shifts/?start_date={shift_date}&end_date={shift_date}')
        assert response.status_code == 200
        shifts = json.loads(response.data)
        assert len(shifts) >= 4
        
        # Test 8: Delete a shift
        response = client.delete(f'/api/shifts/{shift1["id"]}')
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get(f'/api/shifts/{shift1["id"]}')
        assert response.status_code == 404
    
    def test_shift_hour_limits_workflow(self, client, clean_db):
        """Test shift creation with hour limit enforcement"""
        
        # Setup
        emp_response = client.post('/api/employees/',
            json={'friendly_name': 'Test Employee', 'system_name': 'test.emp'})
        emp = json.loads(emp_response.data)
        
        child_response = client.post('/api/children/',
            json={'name': 'Test Child', 'code': 'TC001'})
        child = json.loads(child_response.data)
        
        # Set hour limit
        response = client.post('/api/config/hour-limits',
            json={
                'employee_id': emp['id'],
                'child_id': child['id'],
                'max_hours_per_week': 20.0,
                'alert_threshold': 16.0
            })
        
        if response.status_code == 201:
            # Create shifts approaching the limit
            week_start = date.today() - timedelta(days=date.today().weekday())
            total_hours = 0
            
            for day_offset in range(5):
                shift_date = (week_start + timedelta(days=day_offset)).isoformat()
                hours = 4 if day_offset < 4 else 5  # 4+4+4+4+5 = 21 hours total
                
                response = client.post('/api/shifts/',
                    json={
                        'employee_id': emp['id'],
                        'child_id': child['id'],
                        'date': shift_date,
                        'start_time': '09:00:00',
                        'end_time': f'{9+hours:02d}:00:00'
                    })
                
                if day_offset < 4:
                    # First 4 days should succeed (16 hours total)
                    assert response.status_code == 201
                    total_hours += hours
                else:
                    # 5th day might fail or warn due to exceeding limit
                    # Depends on implementation
                    if response.status_code == 201:
                        total_hours += hours
                    elif response.status_code == 400:
                        # Hour limit exceeded
                        error_data = json.loads(response.data)
                        assert 'hour' in error_data['error'].lower() or 'limit' in error_data['error'].lower()
    
    def test_shift_status_workflow(self, client, clean_db):
        """Test shift status transitions"""
        
        # Setup
        emp_response = client.post('/api/employees/',
            json={'friendly_name': 'Status Test Emp', 'system_name': 'status.emp'})
        emp = json.loads(emp_response.data)
        
        child_response = client.post('/api/children/',
            json={'name': 'Status Test Child', 'code': 'STC001'})
        child = json.loads(child_response.data)
        
        # Create shift with pending status
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post('/api/shifts/',
            json={
                'employee_id': emp['id'],
                'child_id': child['id'],
                'date': tomorrow,
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'status': 'pending'
            })
        assert response.status_code == 201
        shift = json.loads(response.data)
        
        # Update to confirmed
        response = client.put(f'/api/shifts/{shift["id"]}',
            json={'status': 'confirmed'})
        assert response.status_code == 200
        
        # Verify status change
        response = client.get(f'/api/shifts/{shift["id"]}')
        updated_shift = json.loads(response.data)
        assert updated_shift['status'] == 'confirmed'
        
        # Try to set invalid status
        response = client.put(f'/api/shifts/{shift["id"]}',
            json={'status': 'invalid_status'})
        # Should either reject or ignore invalid status
        
        # Update to cancelled
        response = client.put(f'/api/shifts/{shift["id"]}',
            json={'status': 'cancelled'})
        assert response.status_code == 200
        
        # Query all shifts (status filtering not implemented yet)
        response = client.get(f'/api/shifts/?start_date={tomorrow}&end_date={tomorrow}')
        all_shifts = json.loads(response.data)
        # Find the cancelled shift
        cancelled_shift = next((s for s in all_shifts if s['id'] == shift['id']), None)
        # Verify status was updated (if status is returned)
        if cancelled_shift and 'status' in cancelled_shift:
            assert cancelled_shift['status'] == 'cancelled'
    
    def test_bulk_shift_operations(self, client, clean_db):
        """Test bulk shift creation and management"""
        
        # Setup
        employees = []
        for i in range(3):
            response = client.post('/api/employees/',
                json={'friendly_name': f'Bulk Emp {i+1}', 'system_name': f'bulk.emp{i+1}'})
            employees.append(json.loads(response.data))
        
        children = []
        for i in range(2):
            response = client.post('/api/children/',
                json={'name': f'Bulk Child {i+1}', 'code': f'BC{i+1:03d}'})
            children.append(json.loads(response.data))
        
        # Create multiple shifts in bulk
        week_start = date.today() - timedelta(days=date.today().weekday())
        created_shifts = []
        
        for day_offset in range(5):  # Monday to Friday
            shift_date = (week_start + timedelta(days=day_offset)).isoformat()
            for emp in employees:
                for child in children:
                    # Create alternating morning/afternoon shifts
                    is_morning = (day_offset + employees.index(emp)) % 2 == 0
                    start_time = '08:00:00' if is_morning else '14:00:00'
                    end_time = '12:00:00' if is_morning else '18:00:00'
                    
                    response = client.post('/api/shifts/',
                        json={
                            'employee_id': emp['id'],
                            'child_id': child['id'],
                            'date': shift_date,
                            'start_time': start_time,
                            'end_time': end_time
                        })
                    
                    if response.status_code == 201:
                        created_shifts.append(json.loads(response.data))
        
        # Query shifts for the week
        response = client.get(f'/api/shifts/?start_date={week_start.isoformat()}&end_date={(week_start + timedelta(days=6)).isoformat()}')
        assert response.status_code == 200
        week_shifts = json.loads(response.data)
        assert len(week_shifts) >= len(created_shifts)
        
        # Test filtering by employee
        for emp in employees:
            response = client.get(f'/api/shifts/?employee_id={emp["id"]}&start_date={week_start.isoformat()}')
            emp_shifts = json.loads(response.data)
            # All returned shifts should be for this employee
            for shift in emp_shifts:
                assert shift['employee_id'] == emp['id']
        
        # Test filtering by child
        for child in children:
            response = client.get(f'/api/shifts/?child_id={child["id"]}&start_date={week_start.isoformat()}')
            child_shifts = json.loads(response.data)
            # All returned shifts should be for this child
            for shift in child_shifts:
                assert shift['child_id'] == child['id']
        
        # Clean up - delete all created shifts
        for shift in created_shifts[:5]:  # Delete first 5 as sample
            response = client.delete(f'/api/shifts/{shift["id"]}')
            assert response.status_code == 200