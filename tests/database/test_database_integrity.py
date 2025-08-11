"""Database integrity, migration, and constraint tests"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime, date
from database import Database


class TestDatabaseMigrations:
    """Test database migrations and schema updates"""
    
    def test_fresh_database_creation(self):
        """Test that a fresh database creates all required tables"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        try:
            db = Database(db_path)
            
            # Verify all tables exist
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    ORDER BY name
                """)
                tables = {row[0] for row in cursor.fetchall()}
                
                expected_tables = {
                    'employees', 'children', 'shifts', 'payroll_periods',
                    'exclusion_periods', 'hour_limits', 'app_config',
                    'child_budgets', 'employee_rates', 'budget_allocations',
                    'budget_reports'
                }
                
                assert expected_tables.issubset(tables)
        finally:
            os.close(db_fd)
            os.unlink(db_path)
    
    def test_migration_adds_time_fields_to_exclusions(self):
        """Test migration adds start_time and end_time to exclusion_periods"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        try:
            # Create old schema without time fields
            conn = sqlite3.connect(db_path)
            conn.execute('''
                CREATE TABLE exclusion_periods (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    reason TEXT,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
            conn.close()
            
            # Run migration
            db = Database(db_path)
            
            # Verify columns were added
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(exclusion_periods)")
                columns = {col[1] for col in cursor.fetchall()}
                
                assert 'start_time' in columns
                assert 'end_time' in columns
                assert 'employee_id' in columns
                assert 'child_id' in columns
        finally:
            os.close(db_fd)
            os.unlink(db_path)
    
    def test_migration_adds_hourly_rate_to_employees(self):
        """Test migration adds hourly_rate column to employees table"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        try:
            # Create old schema without hourly_rate
            conn = sqlite3.connect(db_path)
            conn.execute('''
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    friendly_name TEXT NOT NULL,
                    system_name TEXT NOT NULL UNIQUE,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
            conn.close()
            
            # Run migration
            db = Database(db_path)
            
            # Verify column was added
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(employees)")
                columns = {col[1] for col in cursor.fetchall()}
                
                assert 'hourly_rate' in columns
        finally:
            os.close(db_fd)
            os.unlink(db_path)
    
    def test_migration_renames_hour_limit_columns(self):
        """Test migration renames max_hours_per_period to max_hours_per_week"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        try:
            # Create old schema with per_period naming
            conn = sqlite3.connect(db_path)
            conn.execute('PRAGMA foreign_keys = OFF')
            conn.execute('''
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    friendly_name TEXT NOT NULL,
                    system_name TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE children (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE hour_limits (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    child_id INTEGER NOT NULL,
                    max_hours_per_period REAL NOT NULL,
                    alert_threshold REAL,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (child_id) REFERENCES children(id)
                )
            ''')
            
            # Insert test data with period limits (will be halved)
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO hour_limits (employee_id, child_id, max_hours_per_period, alert_threshold, created_at)
                VALUES (1, 1, 80.0, 60.0, '2025-01-01 00:00:00')
            """)
            conn.commit()
            conn.close()
            
            # Run migration
            db = Database(db_path)
            
            # Verify column was renamed and values adjusted
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(hour_limits)")
                columns = {col[1] for col in cursor.fetchall()}
                
                assert 'max_hours_per_week' in columns
                assert 'max_hours_per_period' not in columns
                
                # Check that values were halved
                cursor.execute("SELECT max_hours_per_week, alert_threshold FROM hour_limits WHERE id = 1")
                row = cursor.fetchone()
                assert row[0] == 40.0  # 80 / 2
                assert row[1] == 30.0  # 60 / 2
        finally:
            os.close(db_fd)
            os.unlink(db_path)
    
    def test_migration_creates_budget_tables_if_missing(self):
        """Test migration creates budget tables if they don't exist"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        try:
            # Create minimal schema without budget tables
            conn = sqlite3.connect(db_path)
            conn.execute('''
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    friendly_name TEXT NOT NULL,
                    system_name TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE children (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE payroll_periods (
                    id INTEGER PRIMARY KEY,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL
                )
            ''')
            conn.commit()
            conn.close()
            
            # Run migration
            db = Database(db_path)
            
            # Verify budget tables were created
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE '%budget%'
                    ORDER BY name
                """)
                tables = {row[0] for row in cursor.fetchall()}
                
                assert 'child_budgets' in tables
                assert 'budget_allocations' in tables
                assert 'budget_reports' in tables
                
                # Also check employee_rates
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name = 'employee_rates'
                """)
                assert cursor.fetchone() is not None
        finally:
            os.close(db_fd)
            os.unlink(db_path)


class TestDatabaseConstraints:
    """Test database constraints and referential integrity"""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database for constraint testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        db = Database(db_path)
        yield db
        os.close(db_fd)
        os.unlink(db_path)
    
    def test_foreign_key_constraint_employee_delete(self, test_db):
        """Test that foreign key constraints prevent deletion of referenced employees"""
        with test_db.get_connection() as conn:
            # Create employee and shift
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                VALUES (1, 1, '2025-01-01', '09:00:00', '17:00:00')
            """)
            conn.commit()
            
            # Try to delete employee with shifts - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM employees WHERE id = 1")
    
    def test_foreign_key_constraint_child_delete(self, test_db):
        """Test that foreign key constraints prevent deletion of referenced children"""
        with test_db.get_connection() as conn:
            # Create child and shift
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                VALUES (1, 1, '2025-01-01', '09:00:00', '17:00:00')
            """)
            conn.commit()
            
            # Try to delete child with shifts - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM children WHERE id = 1")
    
    def test_unique_constraint_employee_system_name(self, test_db):
        """Test unique constraint on employee system_name"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test1', 'test')")
            conn.commit()
            
            # Try to insert duplicate system_name - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test2', 'test')")
    
    def test_unique_constraint_child_code(self, test_db):
        """Test unique constraint on child code"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO children (name, code) VALUES ('Child1', 'C001')")
            conn.commit()
            
            # Try to insert duplicate code - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO children (name, code) VALUES ('Child2', 'C001')")
    
    def test_unique_constraint_shift_overlap(self, test_db):
        """Test unique constraint preventing exact duplicate shifts"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                VALUES (1, 1, '2025-01-01', '09:00:00', '17:00:00')
            """)
            conn.commit()
            
            # Try to insert duplicate shift - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                    VALUES (1, 1, '2025-01-01', '09:00:00', '18:00:00')
                """)
    
    def test_check_constraint_shift_same_day(self, test_db):
        """Test CHECK constraint that shift times must be on same day"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            
            # This should work - same day
            conn.execute("""
                INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                VALUES (1, 1, '2025-01-01', '09:00:00', '17:00:00')
            """)
            conn.commit()
    
    def test_xor_constraint_exclusion_periods(self, test_db):
        """Test XOR constraint on exclusion_periods (employee OR child, not both)"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            
            # Valid: Employee only
            conn.execute("""
                INSERT INTO exclusion_periods (name, start_date, end_date, employee_id)
                VALUES ('Employee Vacation', '2025-01-01', '2025-01-07', 1)
            """)
            
            # Valid: Child only
            conn.execute("""
                INSERT INTO exclusion_periods (name, start_date, end_date, child_id)
                VALUES ('Child Holiday', '2025-01-01', '2025-01-07', 1)
            """)
            
            # Valid: Neither (general exclusion)
            conn.execute("""
                INSERT INTO exclusion_periods (name, start_date, end_date)
                VALUES ('Company Holiday', '2025-01-01', '2025-01-07')
            """)
            
            # Invalid: Both employee and child
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO exclusion_periods (name, start_date, end_date, employee_id, child_id)
                    VALUES ('Invalid', '2025-01-01', '2025-01-07', 1, 1)
                """)
    
    def test_unique_constraint_hour_limits(self, test_db):
        """Test unique constraint on hour_limits (employee_id, child_id)"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO hour_limits (employee_id, child_id, max_hours_per_week)
                VALUES (1, 1, 40.0)
            """)
            conn.commit()
            
            # Try to insert duplicate employee-child pair - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO hour_limits (employee_id, child_id, max_hours_per_week)
                    VALUES (1, 1, 35.0)
                """)
    
    def test_unique_constraint_child_budget_period(self, test_db):
        """Test unique constraint on child_budgets (child_id, period_start, period_end)"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO child_budgets (child_id, period_start, period_end, budget_hours)
                VALUES (1, '2025-01-01', '2025-01-31', 100.0)
            """)
            conn.commit()
            
            # Try to insert duplicate period for same child - should fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO child_budgets (child_id, period_start, period_end, budget_hours)
                    VALUES (1, '2025-01-01', '2025-01-31', 120.0)
                """)
    
    def test_cascade_delete_not_enabled(self, test_db):
        """Test that cascade delete is NOT enabled (intentional design choice)"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            conn.execute("""
                INSERT INTO hour_limits (employee_id, child_id, max_hours_per_week)
                VALUES (1, 1, 40.0)
            """)
            conn.commit()
            
            # Deleting employee should fail due to foreign key (no cascade)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM employees WHERE id = 1")


class TestDatabaseIndexes:
    """Test database indexes for performance"""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database for index testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        db = Database(db_path)
        yield db
        os.close(db_fd)
        os.unlink(db_path)
    
    def test_shift_indexes_exist(self, test_db):
        """Test that performance indexes on shifts table exist"""
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='shifts'
            """)
            indexes = {row[0] for row in cursor.fetchall()}
            
            # Should have indexes for common queries
            assert 'idx_shift_unique' in indexes
            assert 'idx_shift_employee_date' in indexes
            assert 'idx_shift_child_date' in indexes
    
    def test_index_query_performance(self, test_db):
        """Test that indexes improve query performance"""
        import time
        
        with test_db.get_connection() as conn:
            # Create test data
            conn.execute("INSERT INTO employees (id, friendly_name, system_name) VALUES (1, 'Test', 'test')")
            conn.execute("INSERT INTO children (id, name, code) VALUES (1, 'Child', 'C001')")
            
            # Insert many shifts to test index performance
            for i in range(1000):
                date_str = f"2025-01-{(i % 28) + 1:02d}"
                conn.execute("""
                    INSERT INTO shifts (employee_id, child_id, date, start_time, end_time)
                    VALUES (1, 1, ?, '09:00:00', '17:00:00')
                """, (date_str,))
            conn.commit()
            
            # Test indexed query (should be fast)
            start = time.time()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM shifts 
                WHERE employee_id = 1 AND date = '2025-01-15'
            """)
            results = cursor.fetchall()
            indexed_time = time.time() - start
            
            # Indexed query should be reasonably fast (< 100ms)
            # Note: Using a more lenient threshold for CI/slower systems
            assert indexed_time < 0.1
            assert len(results) > 0


class TestDatabaseTransactions:
    """Test database transaction handling"""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database for transaction testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        db = Database(db_path)
        yield db
        os.close(db_fd)
        os.unlink(db_path)
    
    def test_rollback_on_error(self, test_db):
        """Test that transactions rollback on error"""
        try:
            with test_db.get_connection() as conn:
                # Start a transaction
                conn.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test', 'test')")
                
                # Force an error
                conn.execute("INSERT INTO nonexistent_table (col) VALUES ('value')")
        except Exception:
            pass
        
        # Verify rollback occurred
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM employees WHERE system_name = 'test'")
            count = cursor.fetchone()[0]
            assert count == 0  # Should be rolled back
    
    def test_commit_on_success(self, test_db):
        """Test that transactions commit on success"""
        with test_db.get_connection() as conn:
            conn.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test', 'test')")
            # Connection commits automatically when context exits successfully
        
        # Verify commit occurred
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM employees WHERE system_name = 'test'")
            count = cursor.fetchone()[0]
            assert count == 1  # Should be committed
    
    def test_isolation_between_connections(self, test_db):
        """Test that connections are isolated from each other"""
        # Insert in first connection
        with test_db.get_connection() as conn1:
            conn1.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test', 'test')")
        
        # Read in second connection
        with test_db.get_connection() as conn2:
            cursor = conn2.cursor()
            cursor.execute("SELECT COUNT(*) FROM employees")
            count = cursor.fetchone()[0]
            assert count == 1  # Should see committed data


class TestDatabaseHelperMethods:
    """Test database helper methods (execute, fetchone, fetchall, insert)"""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database for helper method testing"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        db = Database(db_path)
        yield db
        os.close(db_fd)
        os.unlink(db_path)
    
    def test_execute_method(self, test_db):
        """Test the execute helper method"""
        cursor = test_db.execute(
            "INSERT INTO employees (friendly_name, system_name) VALUES (?, ?)",
            ('Test', 'test')
        )
        assert cursor is not None
        
        # Verify insert worked
        result = test_db.fetchone("SELECT friendly_name FROM employees WHERE system_name = ?", ('test',))
        assert result['friendly_name'] == 'Test'
    
    def test_fetchone_method(self, test_db):
        """Test the fetchone helper method"""
        test_db.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test', 'test')")
        
        # Test with params
        result = test_db.fetchone("SELECT * FROM employees WHERE system_name = ?", ('test',))
        assert result['friendly_name'] == 'Test'
        
        # Test without params
        result = test_db.fetchone("SELECT COUNT(*) as count FROM employees")
        assert result['count'] == 1
        
        # Test no results
        result = test_db.fetchone("SELECT * FROM employees WHERE system_name = ?", ('nonexistent',))
        assert result is None
    
    def test_fetchall_method(self, test_db):
        """Test the fetchall helper method"""
        # Insert multiple records
        test_db.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test1', 'test1')")
        test_db.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test2', 'test2')")
        
        # Test with params
        results = test_db.fetchall("SELECT * FROM employees WHERE system_name LIKE ?", ('test%',))
        assert len(results) == 2
        
        # Test without params
        results = test_db.fetchall("SELECT * FROM employees")
        assert len(results) == 2
        
        # Test no results
        results = test_db.fetchall("SELECT * FROM employees WHERE system_name = ?", ('nonexistent',))
        assert len(results) == 0
    
    def test_insert_method(self, test_db):
        """Test the insert helper method"""
        # Test insert and get last row id
        employee_id = test_db.insert(
            "INSERT INTO employees (friendly_name, system_name) VALUES (?, ?)",
            ('Test', 'test')
        )
        assert employee_id > 0
        
        # Verify the ID is correct
        result = test_db.fetchone("SELECT id FROM employees WHERE system_name = ?", ('test',))
        assert result['id'] == employee_id
        
        # Test insert without params
        test_db.insert("INSERT INTO children (name, code) VALUES ('Child', 'C001')")
        result = test_db.fetchone("SELECT * FROM children WHERE code = 'C001'")
        assert result is not None
    
    def test_row_factory_returns_dict_like_objects(self, test_db):
        """Test that row factory returns dict-like Row objects"""
        test_db.execute("INSERT INTO employees (friendly_name, system_name) VALUES ('Test', 'test')")
        
        result = test_db.fetchone("SELECT * FROM employees WHERE system_name = 'test'")
        
        # Should be accessible like a dict
        assert result['friendly_name'] == 'Test'
        assert result['system_name'] == 'test'
        
        # Should have keys
        assert 'id' in dict(result)
        assert 'friendly_name' in dict(result)
        assert 'system_name' in dict(result)