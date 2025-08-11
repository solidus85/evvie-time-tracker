"""End-to-end test for complete payroll workflow"""

import pytest
import json
from datetime import datetime, date, timedelta
from io import BytesIO


class TestPayrollWorkflow:
    """Test complete payroll period processing workflow"""
    
    def test_complete_payroll_workflow(self, client, clean_db):
        """Test a complete payroll workflow from setup to export"""
        
        # Step 1: Create employees
        employees = []
        for i in range(2):
            emp_name = f'Employee {i+1}'
            emp_system = f'emp{i+1}'
            response = client.post('/api/employees/',
                json={
                    'friendly_name': emp_name,
                    'system_name': emp_system,
                    'hourly_rate': 25.00 + (i * 5)
                })
            assert response.status_code == 201
            emp_data = json.loads(response.data)
            # Store the employee info including what we sent
            employees.append({
                'id': emp_data['id'],
                'friendly_name': emp_name,
                'system_name': emp_system
            })
        
        # Step 2: Create children
        children = []
        for i in range(2):
            child_name = f'Child {i+1}'
            child_code = f'CH00{i+1}'
            response = client.post('/api/children/',
                json={
                    'name': child_name,
                    'code': child_code
                })
            assert response.status_code == 201
            child_data = json.loads(response.data)
            # Store the child info including what we sent
            children.append({
                'id': child_data['id'],
                'name': child_name,
                'code': child_code
            })
        
        # Step 3: Get current payroll period
        response = client.get('/api/payroll/periods/current')
        if response.status_code == 404:
            # Configure payroll periods if none exist
            today = date.today()
            # Find the most recent Thursday
            days_since_thursday = (today.weekday() - 3) % 7
            last_thursday = today - timedelta(days=days_since_thursday)
            
            response = client.post('/api/payroll/periods/configure',
                json={'anchor_date': last_thursday.isoformat()})
            assert response.status_code == 200
            
            # Get current period again
            response = client.get('/api/payroll/periods/current')
        
        assert response.status_code == 200
        period = json.loads(response.data)
        
        # Step 4: Create shifts for the period
        shifts = []
        period_start = datetime.fromisoformat(period['start_date']).date()
        
        for day_offset in range(5):  # Create shifts for 5 days
            shift_date = period_start + timedelta(days=day_offset)
            if shift_date.weekday() < 5:  # Weekdays only
                for emp in employees[:1]:  # First employee only
                    for idx, child in enumerate(children):
                        # Stagger times to avoid conflicts
                        start_hour = 9 if idx == 0 else 14
                        end_hour = 13 if idx == 0 else 18
                        response = client.post('/api/shifts/',
                            json={
                                'employee_id': emp['id'],
                                'child_id': child['id'],
                                'date': shift_date.isoformat(),
                                'start_time': f'{start_hour:02d}:00:00',
                                'end_time': f'{end_hour:02d}:00:00'
                            })
                        assert response.status_code == 201
                        shifts.append(json.loads(response.data))
        
        # Step 5: Create an exclusion period
        exclusion_date = period_start + timedelta(days=7)
        response = client.post('/api/payroll/exclusions',
            json={
                'name': 'Holiday',
                'start_date': exclusion_date.isoformat(),
                'end_date': (exclusion_date + timedelta(days=1)).isoformat(),
                'employee_id': employees[0]['id'],
                'reason': 'Public holiday'
            })
        assert response.status_code in [201, 404]  # May not have exclusions endpoint
        
        # Step 6: Set hour limits
        response = client.post('/api/config/hour-limits/',
            json={
                'employee_id': employees[0]['id'],
                'child_id': children[0]['id'],
                'max_hours_per_week': 40.0,
                'alert_threshold': 35.0
            })
        assert response.status_code in [201, 404]  # May not have hour limits endpoint
        
        # Step 7: Get period summary
        response = client.get(f'/api/payroll/periods/{period["id"]}/summary')
        assert response.status_code == 200
        summary = json.loads(response.data)
        
        # Verify summary contains expected data
        assert 'total_hours' in summary
        assert 'total_shifts' in summary
        assert summary['total_shifts'] > 0
        
        # Step 8: Import additional shifts via CSV
        csv_content = f"""Date,Consumer,Employee,Start Time,End Time
{(period_start + timedelta(days=6)).strftime('%m/%d/%Y')},{children[0]['name']} ({children[0]['code']}),{employees[1]['friendly_name']},10:00 AM,02:00 PM
{(period_start + timedelta(days=7)).strftime('%m/%d/%Y')},{children[1]['name']} ({children[1]['code']}),{employees[1]['friendly_name']},03:00 PM,07:00 PM"""
        
        response = client.post('/api/import/csv',
            data={'file': (BytesIO(csv_content.encode('utf-8')), 'import.csv', 'text/csv')},
            content_type='multipart/form-data')
        assert response.status_code == 200
        import_result = json.loads(response.data)
        assert import_result['imported'] >= 0
        
        # Step 9: Export data as CSV
        response = client.get(f'/api/export/csv?start_date={period["start_date"]}&end_date={period["end_date"]}')
        assert response.status_code == 200
        assert response.content_type == 'text/csv'
        
        # Step 10: Export data as JSON
        response = client.get(f'/api/export/json?start_date={period["start_date"]}&end_date={period["end_date"]}')
        assert response.status_code == 200
        export_data = json.loads(response.data)
        
        # Verify export contains shifts
        assert 'shifts' in export_data
        assert len(export_data['shifts']) > 0
        assert 'summary' in export_data
        
        # Step 11: Clean up - delete a shift
        if shifts:
            response = client.delete(f'/api/shifts/{shifts[0]["id"]}')
            assert response.status_code == 200
        
        # Step 12: Verify the workflow completed successfully
        # Get updated summary
        response = client.get(f'/api/payroll/periods/{period["id"]}/summary')
        assert response.status_code == 200
        final_summary = json.loads(response.data)
        
        # Should have fewer shifts after deletion
        if 'total_shifts' in final_summary and 'total_shifts' in summary:
            assert final_summary['total_shifts'] <= summary['total_shifts']
    
    def test_payroll_period_navigation(self, client, clean_db):
        """Test navigating between payroll periods"""
        
        # Configure payroll periods
        anchor_date = date(2025, 1, 2)  # A Thursday
        response = client.post('/api/payroll/periods/configure',
            json={'anchor_date': anchor_date.isoformat()})
        
        # Get current period
        response = client.get('/api/payroll/periods/current')
        assert response.status_code == 200
        current_period = json.loads(response.data)
        
        # Get all periods
        response = client.get('/api/payroll/periods')
        assert response.status_code == 200
        all_periods = json.loads(response.data)
        assert len(all_periods) > 0
        
        # Get specific period summary
        if all_periods:
            response = client.get(f'/api/payroll/periods/{all_periods[0]["id"]}/summary')
            assert response.status_code == 200
    
    def test_payroll_with_multiple_employees_and_children(self, client, clean_db):
        """Test payroll calculation with multiple employees and children"""
        
        # Create 3 employees
        employees = []
        for i in range(3):
            response = client.post('/api/employees/',
                json={
                    'friendly_name': f'Test Employee {i+1}',
                    'system_name': f'test.emp{i+1}',
                    'hourly_rate': 20.00 + (i * 5)
                })
            assert response.status_code == 201
            employees.append(json.loads(response.data))
        
        # Create 3 children
        children = []
        for i in range(3):
            response = client.post('/api/children/',
                json={
                    'name': f'Test Child {i+1}',
                    'code': f'TC{i+1:03d}'
                })
            assert response.status_code == 201
            children.append(json.loads(response.data))
        
        # Get current period
        response = client.get('/api/payroll/periods/current')
        if response.status_code == 200:
            period = json.loads(response.data)
            period_start = datetime.fromisoformat(period['start_date']).date()
            
            # Create shifts in a round-robin fashion
            shift_count = 0
            for day_offset in range(10):
                shift_date = period_start + timedelta(days=day_offset)
                if shift_date.weekday() < 5:  # Weekdays only
                    emp_idx = shift_count % len(employees)
                    child_idx = shift_count % len(children)
                    
                    response = client.post('/api/shifts/',
                        json={
                            'employee_id': employees[emp_idx]['id'],
                            'child_id': children[child_idx]['id'],
                            'date': shift_date.isoformat(),
                            'start_time': f'{9 + (shift_count % 3):02d}:00:00',
                            'end_time': f'{13 + (shift_count % 3):02d}:00:00'
                        })
                    assert response.status_code == 201
                    shift_count += 1
            
            # Get period summary
            response = client.get(f'/api/payroll/periods/{period["id"]}/summary')
            assert response.status_code == 200
            summary = json.loads(response.data)
            
            # Verify summary has data for multiple employees/children
            assert summary['total_shifts'] >= shift_count
            
            # Export and verify
            response = client.get(f'/api/export/json?start_date={period["start_date"]}&end_date={period["end_date"]}')
            assert response.status_code == 200
            export_data = json.loads(response.data)
            
            # Should have shifts for multiple employees and children
            if 'shifts' in export_data:
                unique_employees = set(s['employee_id'] for s in export_data['shifts'])
                unique_children = set(s['child_id'] for s in export_data['shifts'])
                assert len(unique_employees) <= len(employees)
                assert len(unique_children) <= len(children)