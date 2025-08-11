"""
Pytest configuration and shared fixtures for all tests.
"""
import os
import sys
import tempfile
from datetime import datetime, date, time, timedelta
from pathlib import Path

import pytest
from flask import Flask
from freezegun import freeze_time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import Database


@pytest.fixture(scope='session')
def app():
    """Create and configure a test Flask application."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Set environment variable for test database
    os.environ['DATABASE'] = db_path
    os.environ['TESTING'] = 'true'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    
    # Create app
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Replace the database with test database
    app.db = Database(db_path)
    
    yield app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)
    if 'DATABASE' in os.environ:
        del os.environ['DATABASE']
    if 'TESTING' in os.environ:
        del os.environ['TESTING']


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db(app):
    """Get a database connection for testing."""
    with app.app_context():
        db_instance = app.db
        with db_instance.get_connection() as conn:
            yield conn


@pytest.fixture(scope='function')
def clean_db(db):
    """Clean the database before each test."""
    # Clean tables in order to respect foreign key constraints
    tables = [
        'budget_allocations',  # References children, employees, payroll_periods
        'employee_rates',      # References employees
        'child_budgets',       # References children
        'budget_reports',      # References children
        'hour_limits',         # References employees and children
        'shifts',              # References employees and children
        'exclusion_periods',   # References employees and children
        'payroll_periods',     # No foreign keys
        'children',            # No foreign keys
        'employees',           # No foreign keys
        'app_config'           # No foreign keys
    ]
    
    # Disable foreign key checks temporarily
    db.execute('PRAGMA foreign_keys = OFF')
    
    for table in tables:
        try:
            db.execute(f'DELETE FROM {table}')
        except Exception:
            pass  # Ignore if table doesn't exist
    
    db.execute('PRAGMA foreign_keys = ON')
    db.commit()
    
    yield db


@pytest.fixture
def sample_employee(clean_db):
    """Create a sample employee."""
    cursor = clean_db.execute(
        'INSERT INTO employees (friendly_name, system_name, hourly_rate, active) VALUES (?, ?, ?, ?)',
        ('John Doe', 'jdoe', 25.50, 1)
    )
    clean_db.commit()
    return {
        'id': cursor.lastrowid,
        'friendly_name': 'John Doe',
        'system_name': 'jdoe',
        'hourly_rate': 25.50,
        'active': 1
    }


@pytest.fixture
def sample_child(clean_db):
    """Create a sample child."""
    cursor = clean_db.execute(
        'INSERT INTO children (name, code, active) VALUES (?, ?, ?)',
        ('Alice Smith', 'AS001', 1)
    )
    clean_db.commit()
    return {
        'id': cursor.lastrowid,
        'name': 'Alice Smith',
        'code': 'AS001',
        'active': 1
    }


@pytest.fixture
def sample_payroll_period(clean_db):
    """Create a sample payroll period."""
    start_date = date(2024, 1, 4)  # Thursday
    end_date = date(2024, 1, 17)   # Wednesday
    
    cursor = clean_db.execute(
        'INSERT INTO payroll_periods (start_date, end_date) VALUES (?, ?)',
        (start_date.isoformat(), end_date.isoformat())
    )
    clean_db.commit()
    return {
        'id': cursor.lastrowid,
        'start_date': start_date,
        'end_date': end_date
    }


@pytest.fixture
def sample_shift(clean_db, sample_employee, sample_child, sample_payroll_period):
    """Create a sample shift."""
    shift_date = date(2024, 1, 8)  # Monday within payroll period
    start_time = time(9, 0)
    end_time = time(17, 0)
    
    cursor = clean_db.execute(
        '''INSERT INTO shifts 
           (employee_id, child_id, date, start_time, end_time, is_imported, status) 
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (sample_employee['id'], sample_child['id'], 
         shift_date.isoformat(), start_time.isoformat(), 
         end_time.isoformat(), 0, 'confirmed')
    )
    clean_db.commit()
    return {
        'id': cursor.lastrowid,
        'employee_id': sample_employee['id'],
        'child_id': sample_child['id'],
        'date': shift_date,
        'start_time': start_time,
        'end_time': end_time,
        'is_imported': 0,
        'status': 'confirmed'
    }


@pytest.fixture
def multiple_employees(clean_db):
    """Create multiple test employees."""
    employees = [
        ('Alice Johnson', 'ajohnson', 30.00, 1),
        ('Bob Wilson', 'bwilson', 25.00, 1),
        ('Charlie Brown', 'cbrown', 28.50, 1),
        ('Diana Prince', 'dprince', 35.00, 0),  # Inactive
    ]
    
    result = []
    for name, sys_name, rate, active in employees:
        cursor = clean_db.execute(
            'INSERT INTO employees (friendly_name, system_name, hourly_rate, active) VALUES (?, ?, ?, ?)',
            (name, sys_name, rate, active)
        )
        result.append({
            'id': cursor.lastrowid,
            'friendly_name': name,
            'system_name': sys_name,
            'hourly_rate': rate,
            'active': active
        })
    
    clean_db.commit()
    return result


@pytest.fixture
def multiple_children(clean_db):
    """Create multiple test children."""
    children = [
        ('Emma Watson', 'EW001', 1),
        ('Oliver James', 'OJ002', 1),
        ('Sophia Lee', 'SL003', 1),
        ('Liam Chen', 'LC004', 0),  # Inactive
    ]
    
    result = []
    for name, code, active in children:
        cursor = clean_db.execute(
            'INSERT INTO children (name, code, active) VALUES (?, ?, ?)',
            (name, code, active)
        )
        result.append({
            'id': cursor.lastrowid,
            'name': name,
            'code': code,
            'active': active
        })
    
    clean_db.commit()
    return result


@pytest.fixture
def frozen_time():
    """Freeze time for consistent testing."""
    with freeze_time("2024-01-08 10:00:00") as frozen:
        yield frozen


@pytest.fixture
def mock_pdf_file(tmp_path):
    """Create a mock PDF file for testing."""
    pdf_path = tmp_path / "test_budget.pdf"
    pdf_path.write_bytes(b'%PDF-1.4\n%%Mock PDF content')
    return str(pdf_path)


@pytest.fixture
def mock_csv_file(tmp_path):
    """Create a mock CSV file for testing."""
    csv_path = tmp_path / "test_import.csv"
    csv_content = """Employee,Child,Date,Start Time,End Time
John Doe,Alice Smith,2024-01-08,09:00,17:00
Jane Doe,Bob Jones,2024-01-08,10:00,18:00"""
    csv_path.write_text(csv_content)
    return str(csv_path)


@pytest.fixture
def auth_headers():
    """Mock authentication headers if needed in future."""
    return {'Authorization': 'Bearer test-token'}


@pytest.fixture
def test_db(app):
    """Create a test database instance for integration tests."""
    return app.db


@pytest.fixture
def sample_data(clean_db, sample_employee, sample_child, sample_payroll_period):
    """Combined fixture for integration tests with common test data."""
    # Create employee and child objects that match the expected structure
    from types import SimpleNamespace
    
    employee = SimpleNamespace(
        id=sample_employee['id'],
        friendly_name=sample_employee['friendly_name'],
        system_name=sample_employee['system_name'],
        hourly_rate=sample_employee['hourly_rate'],
        active=sample_employee['active']
    )
    
    child = SimpleNamespace(
        id=sample_child['id'],
        name=sample_child['name'],
        code=sample_child['code'],
        active=sample_child['active']
    )
    
    period = SimpleNamespace(
        id=sample_payroll_period['id'],
        start_date=sample_payroll_period['start_date'].isoformat(),
        end_date=sample_payroll_period['end_date'].isoformat()
    )
    
    return {
        'employee': employee,
        'child': child,
        'payroll_period': period
    }


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "skip_ci: Skip in CI environment")