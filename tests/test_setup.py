"""
Test to verify the testing infrastructure is properly set up.
"""
import pytest
from datetime import date

def test_pytest_is_working():
    """Verify pytest is installed and working."""
    assert True

def test_imports_are_working():
    """Verify we can import project modules."""
    from database import Database
    from services.employee_service import EmployeeService
    assert Database is not None
    assert EmployeeService is not None

def test_fixtures_are_working(app, client, clean_db):
    """Verify test fixtures are properly configured."""
    assert app is not None
    assert client is not None
    assert clean_db is not None

def test_sample_data_fixtures(sample_employee, sample_child, sample_shift):
    """Verify sample data fixtures work correctly."""
    assert sample_employee['friendly_name'] == 'John Doe'
    assert sample_child['name'] == 'Alice Smith'
    assert sample_shift['employee_id'] == sample_employee['id']
    assert sample_shift['child_id'] == sample_child['id']

def test_factories_are_working():
    """Verify test factories are properly configured."""
    from tests.fixtures.factories import EmployeeFactory, ChildFactory
    
    employee = EmployeeFactory.create()
    assert 'friendly_name' in employee
    assert 'system_name' in employee
    
    child = ChildFactory.create()
    assert 'name' in child
    assert 'code' in child

@pytest.mark.unit
def test_markers_are_working():
    """Verify custom markers are registered."""
    assert True

def test_database_operations(clean_db):
    """Verify database operations work in tests."""
    # Insert test data
    cursor = clean_db.execute(
        'INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)',
        ('Test User', 'tuser', 1)
    )
    clean_db.commit()
    
    # Query the data
    result = clean_db.execute('SELECT * FROM employees WHERE system_name = ?', ('tuser',)).fetchone()
    assert result is not None
    assert result['friendly_name'] == 'Test User'