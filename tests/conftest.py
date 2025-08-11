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
    # Clean all tables except schema info
    tables = [
        'shifts', 'exclusion_periods', 'hour_limits', 
        'payroll_periods', 'children', 'employees',
        'child_budgets', 'employee_rates', 'budget_allocations',
        'budget_reports', 'app_config'
    ]
    
    for table in tables:
        db.execute(f'DELETE FROM {table}')
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