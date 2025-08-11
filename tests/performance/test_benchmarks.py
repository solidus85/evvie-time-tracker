"""Performance benchmark tests for critical operations"""

import pytest
import time
from datetime import date, timedelta
import random
import string


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical operations"""
    
    @pytest.mark.benchmark
    def test_shift_creation_performance(self, client, sample_data, benchmark):
        """Benchmark shift creation performance"""
        def create_shift():
            return client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': date.today().isoformat(),
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
        
        result = benchmark(create_shift)
        assert result.status_code in [201, 409]  # 409 if duplicate
    
    @pytest.mark.benchmark
    def test_bulk_shift_query_performance(self, client, sample_data, benchmark):
        """Benchmark querying large number of shifts"""
        # Create many shifts first
        base_date = date.today() - timedelta(days=90)
        for i in range(50):
            shift_date = base_date + timedelta(days=i)
            client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': shift_date.isoformat(),
                    'start_time': f'{9 + (i % 8)}:00:00',
                    'end_time': f'{17 + (i % 3)}:00:00'
                })
        
        def query_shifts():
            return client.get('/api/shifts/',
                query_string={
                    'start_date': (base_date - timedelta(days=1)).isoformat(),
                    'end_date': (base_date + timedelta(days=60)).isoformat()
                })
        
        result = benchmark(query_shifts)
        assert result.status_code == 200
    
    @pytest.mark.benchmark
    def test_payroll_calculation_performance(self, client, sample_data, benchmark):
        """Benchmark payroll period calculation performance"""
        # Configure payroll periods
        client.post('/api/payroll/periods/configure',
            json={'anchor_date': '2025-01-02'})
        
        # Create shifts for payroll calculation
        for i in range(20):
            shift_date = date.today() - timedelta(days=i)
            client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': shift_date.isoformat(),
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
        
        def calculate_payroll():
            period_response = client.get('/api/payroll/periods/current')
            if period_response.status_code == 200:
                period = period_response.json
                return client.get(f'/api/payroll/periods/{period["id"]}/summary')
            return period_response
        
        result = benchmark(calculate_payroll)
        assert result.status_code in [200, 404]
    
    @pytest.mark.benchmark
    def test_csv_import_performance(self, client, sample_data, benchmark):
        """Benchmark CSV import performance"""
        # Generate CSV with many rows
        csv_rows = ['Date,Consumer,Employee,Start Time,End Time']
        base_date = date.today() - timedelta(days=30)
        
        for i in range(100):
            shift_date = base_date + timedelta(days=i % 30)
            csv_rows.append(
                f'{shift_date.strftime("%m/%d/%Y")},'
                f'{sample_data["child"].name} ({sample_data["child"].code}),'
                f'{sample_data["employee"].friendly_name},'
                f'{9 + (i % 8)}:00 AM,'
                f'{5 + (i % 3)}:00 PM'
            )
        
        csv_content = '\n'.join(csv_rows)
        
        def import_csv():
            from io import BytesIO
            return client.post('/api/import/csv',
                data={'file': (BytesIO(csv_content.encode('utf-8')), 'perf.csv', 'text/csv')},
                content_type='multipart/form-data')
        
        result = benchmark(import_csv)
        assert result.status_code == 200
    
    @pytest.mark.benchmark
    def test_database_query_performance(self, test_db, benchmark):
        """Benchmark database query performance"""
        # Insert test data
        with test_db.get_connection() as conn:
            # Create employees and track their IDs
            employee_ids = []
            for i in range(10):
                cursor = conn.execute(
                    "INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)",
                    (f'Employee {i}', f'emp{i}', 1)
                )
                employee_ids.append(cursor.lastrowid)
            
            # Create children and track their IDs
            child_ids = []
            for i in range(10):
                cursor = conn.execute(
                    "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
                    (f'Child {i}', f'CH{i:03d}', 1)
                )
                child_ids.append(cursor.lastrowid)
            
            # Create many shifts using actual IDs
            base_date = date.today() - timedelta(days=180)
            for day in range(180):
                for emp_id in employee_ids[:5]:  # Use first 5 employees
                    for child_id in child_ids[:5]:  # Use first 5 children
                        shift_date = base_date + timedelta(days=day)
                        conn.execute(
                            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                               VALUES (?, ?, ?, ?, ?)""",
                            (emp_id, child_id, shift_date.isoformat(), '09:00:00', '17:00:00')
                        )
        
        def complex_query():
            with test_db.get_connection() as conn:
                return conn.execute("""
                    SELECT 
                        e.friendly_name,
                        c.name,
                        COUNT(*) as shift_count,
                        SUM(
                            (strftime('%s', end_time) - strftime('%s', start_time)) / 3600.0
                        ) as total_hours
                    FROM shifts s
                    JOIN employees e ON s.employee_id = e.id
                    JOIN children c ON s.child_id = c.id
                    WHERE s.date >= date('now', '-30 days')
                    GROUP BY e.id, c.id
                    ORDER BY total_hours DESC
                    LIMIT 10
                """).fetchall()
        
        result = benchmark(complex_query)
        assert len(result) >= 0


class TestConcurrentOperations:
    """Test concurrent operation handling"""
    
    def test_concurrent_shift_creation(self, client, sample_data):
        """Test handling concurrent shift creation"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_shift(date_offset):
            shift_date = date.today() + timedelta(days=date_offset)
            response = client.post('/api/shifts/',
                json={
                    'employee_id': sample_data['employee'].id,
                    'child_id': sample_data['child'].id,
                    'date': shift_date.isoformat(),
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                })
            results.put(response.status_code)
        
        # Create threads for concurrent requests
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_shift, args=(i + 100,))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)
        
        # Check results
        success_count = 0
        while not results.empty():
            status = results.get()
            if status == 201:
                success_count += 1
        
        assert success_count >= 8  # At least 80% should succeed
    
    def test_concurrent_csv_import(self, client, sample_data):
        """Test handling concurrent CSV imports"""
        import threading
        import queue
        from io import BytesIO
        
        results = queue.Queue()
        
        def import_csv(file_num):
            csv_content = f"""Date,Consumer,Employee,Start Time,End Time
{date.today().isoformat()},{sample_data['child'].name},{sample_data['employee'].friendly_name},0{file_num}:00 AM,0{file_num}:30 AM"""
            
            response = client.post('/api/import/csv',
                data={'file': (BytesIO(csv_content.encode('utf-8')), f'concurrent{file_num}.csv', 'text/csv')},
                content_type='multipart/form-data')
            results.put(response.status_code)
        
        # Create threads for concurrent imports
        threads = []
        for i in range(5):
            t = threading.Thread(target=import_csv, args=(i + 1,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        # Check results
        success_count = 0
        while not results.empty():
            status = results.get()
            if status == 200:
                success_count += 1
        
        assert success_count >= 3  # At least 60% should succeed


class TestDataIntegrity:
    """Test data integrity under stress"""
    
    def test_large_dataset_handling(self, test_db):
        """Test handling large datasets"""
        with test_db.get_connection() as conn:
            # Create large dataset and get the actual IDs
            cursor = conn.execute("INSERT INTO employees (friendly_name, system_name, active) VALUES ('Test', 'test', 1)")
            emp_id = cursor.lastrowid
            cursor = conn.execute("INSERT INTO children (name, code, active) VALUES ('Child', 'C001', 1)")
            child_id = cursor.lastrowid
            
            # Insert many shifts using actual IDs
            base_date = date.today() - timedelta(days=365)
            for day in range(365):
                shift_date = base_date + timedelta(days=day)
                conn.execute(
                    """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                       VALUES (?, ?, ?, ?, ?)""",
                    (emp_id, child_id, shift_date.isoformat(), '09:00:00', '17:00:00')
                )
            
            # Query large dataset
            result = conn.execute(
                """SELECT COUNT(*) as count, 
                          SUM((strftime('%s', end_time) - strftime('%s', start_time)) / 3600.0) as total_hours
                   FROM shifts"""
            ).fetchone()
            
            assert result['count'] == 365
            assert result['total_hours'] == 365 * 8  # 8 hours per day
    
    def test_transaction_isolation(self, test_db):
        """Test transaction isolation and rollback"""
        try:
            with test_db.get_connection() as conn:
                # Start transaction
                conn.execute("INSERT INTO employees (friendly_name, system_name, active) VALUES ('Trans Test', 'trans', 1)")
                emp_id = conn.lastrowid
                
                # Force an error to trigger rollback
                conn.execute("INSERT INTO invalid_table (col) VALUES ('test')")
        except Exception:
            pass
        
        # Verify rollback occurred
        with test_db.get_connection() as conn:
            result = conn.execute("SELECT * FROM employees WHERE system_name = 'trans'").fetchone()
            assert result is None  # Should be rolled back
    
    def test_constraint_enforcement_under_load(self, test_db):
        """Test constraint enforcement with many operations"""
        with test_db.get_connection() as conn:
            # Use unique names to avoid conflicts with other tests
            cursor = conn.execute("INSERT INTO employees (friendly_name, system_name, active) VALUES ('Constraint Test', 'constraint_test', 1)")
            emp_id = cursor.lastrowid
            cursor = conn.execute("INSERT INTO children (name, code, active) VALUES ('Constraint Child', 'CC001', 1)")
            child_id = cursor.lastrowid
            
            # Try to create many duplicate shifts (should fail)
            duplicate_count = 0
            for i in range(100):
                try:
                    conn.execute(
                        """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                           VALUES (?, ?, '2025-01-01', '09:00:00', '17:00:00')""",
                        (emp_id, child_id)
                    )
                except Exception:
                    duplicate_count += 1
            
            # First insert should succeed, rest should fail
            assert duplicate_count == 99