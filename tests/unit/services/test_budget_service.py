"""Unit tests for BudgetService"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, date
from services.budget_service import BudgetService


class TestBudgetService:
    """Test suite for BudgetService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a BudgetService instance with mock database"""
        return BudgetService(mock_db)
    
    @pytest.fixture
    def sample_budget(self):
        """Sample budget data"""
        return {
            'id': 1,
            'child_id': 1,
            'child_name': 'Jane Smith',
            'child_code': 'JS001',
            'period_start': '2025-01-01',
            'period_end': '2025-01-31',
            'budget_amount': 5000.00,
            'budget_hours': 200.0,
            'notes': 'Monthly budget'
        }
    
    @pytest.fixture
    def sample_budget_report(self):
        """Sample budget report from PDF"""
        return {
            'id': 1,
            'child_id': 1,
            'report_date': '2025-01-15',
            'period_start': '2025-01-01',
            'period_end': '2025-01-31',
            'total_budgeted': 5000.00,
            'total_spent': 3000.00,
            'report_data': json.dumps({
                'employee_spending_summary': {
                    'John Doe': {
                        'total_hours': 100,
                        'total_amount': 2500
                    },
                    'Jane Doe': {
                        'total_hours': 20,
                        'total_amount': 500
                    }
                }
            }),
            'created_at': '2025-01-15 10:00:00'
        }
    
    # Test get_child_budgets
    def test_get_child_budgets_all(self, service, mock_db, sample_budget):
        """Test retrieving all child budgets"""
        mock_db.fetchall.return_value = [sample_budget]
        
        result = service.get_child_budgets()
        
        # Verify query structure
        call_args = mock_db.fetchall.call_args[0]
        assert 'JOIN children c' in call_args[0]
        assert "cb.period_end >= date('now')" in call_args[0]  # Active only by default
        assert 'ORDER BY cb.period_start DESC' in call_args[0]
        assert result == [sample_budget]
    
    def test_get_child_budgets_for_specific_child(self, service, mock_db):
        """Test retrieving budgets for specific child"""
        mock_db.fetchall.return_value = []
        
        service.get_child_budgets(child_id=1)
        
        call_args = mock_db.fetchall.call_args[0]
        assert 'AND cb.child_id = ?' in call_args[0]
        assert 1 in call_args[1]
    
    def test_get_child_budgets_include_inactive(self, service, mock_db):
        """Test retrieving all budgets including inactive"""
        mock_db.fetchall.return_value = []
        
        service.get_child_budgets(active_only=False)
        
        call_args = mock_db.fetchall.call_args[0]
        assert "cb.period_end >= date('now')" not in call_args[0]
    
    # Test get_budget_for_period
    def test_get_budget_for_period_manual_budget(self, service, mock_db, sample_budget):
        """Test getting manual budget for period"""
        mock_db.fetchone.return_value = sample_budget
        
        result = service.get_budget_for_period(1, '2025-01-01', '2025-01-31')
        
        assert result == sample_budget
        # Should only call fetchone once for manual budget
        assert mock_db.fetchone.call_count == 1
    
    def test_get_budget_for_period_from_report(self, service, mock_db, sample_budget_report):
        """Test getting budget from PDF report when no manual budget"""
        mock_db.fetchone.side_effect = [None, sample_budget_report]  # No manual, then report
        
        result = service.get_budget_for_period(1, '2025-01-01', '2025-01-31')
        
        assert result is not None
        assert result['id'] is None  # Indicates from report
        assert result['budget_amount'] == 5000.00
        assert result['budget_hours'] == 200.0  # Calculated from report data (5000 / 25)
        assert 'From PDF report' in result['notes']
    
    def test_get_budget_for_period_not_found(self, service, mock_db):
        """Test getting budget when none exists"""
        mock_db.fetchone.side_effect = [None, None]  # No manual, no report
        
        result = service.get_budget_for_period(1, '2025-01-01', '2025-01-31')
        
        assert result is None
    
    def test_get_budget_for_period_invalid_report_data(self, service, mock_db):
        """Test handling invalid JSON in report data"""
        report = {
            'id': 1,
            'child_id': 1,
            'period_start': '2025-01-01',
            'period_end': '2025-01-31',
            'total_budgeted': 5000.00,
            'report_data': 'invalid json'
        }
        mock_db.fetchone.side_effect = [None, report]
        
        result = service.get_budget_for_period(1, '2025-01-01', '2025-01-31')
        
        assert result is None  # Should fail gracefully
    
    # Test create_child_budget
    def test_create_child_budget_new(self, service, mock_db):
        """Test creating new child budget"""
        mock_db.fetchone.side_effect = [None, None]  # No existing budget
        mock_db.insert.return_value = 1
        
        result = service.create_child_budget(
            1, '2025-01-01', '2025-01-31',
            budget_amount=5000.00, budget_hours=200.0, notes='Test'
        )
        
        assert result == 1
        mock_db.insert.assert_called_once_with(
            """INSERT INTO child_budgets 
               (child_id, period_start, period_end, budget_amount, budget_hours, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (1, '2025-01-01', '2025-01-31', 5000.00, 200.0, 'Test')
        )
    
    def test_create_child_budget_update_existing(self, service, mock_db, sample_budget):
        """Test updating existing budget when creating duplicate period"""
        mock_db.fetchone.return_value = sample_budget
        
        with patch.object(service, 'update_child_budget', return_value=1) as mock_update:
            result = service.create_child_budget(
                1, '2025-01-01', '2025-01-31',
                budget_amount=6000.00
            )
            
            mock_update.assert_called_once_with(1, 6000.00, None, None)
            assert result == 1
    
    # Test update_child_budget
    def test_update_child_budget(self, service, mock_db):
        """Test updating child budget"""
        result = service.update_child_budget(1, 6000.00, 240.0, 'Updated')
        
        assert result == 1
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0]
        assert 'UPDATE child_budgets' in call_args[0]
        assert 'updated_at = CURRENT_TIMESTAMP' in call_args[0]
        assert call_args[1] == (6000.00, 240.0, 'Updated', 1)
    
    def test_update_child_budget_partial(self, service, mock_db):
        """Test partial update of child budget"""
        result = service.update_child_budget(1, budget_amount=6000.00)
        
        assert result == 1
        call_args = mock_db.execute.call_args[0]
        assert call_args[1] == (6000.00, None, None, 1)
    
    # Test delete_child_budget
    def test_delete_child_budget(self, service, mock_db):
        """Test deleting child budget"""
        service.delete_child_budget(1)
        
        mock_db.execute.assert_called_once_with(
            "DELETE FROM child_budgets WHERE id = ?",
            (1,)
        )
    
    # Test employee rates management
    def test_get_employee_rates(self, service, mock_db):
        """Test retrieving employee rates"""
        rates = [{
            'id': 1,
            'employee_id': 1,
            'employee_name': 'John Doe',
            'hourly_rate': 25.00,
            'effective_date': '2025-01-01',
            'end_date': None
        }]
        mock_db.fetchall.return_value = rates
        
        result = service.get_employee_rates()
        
        assert result == rates
        call_args = mock_db.fetchall.call_args[0][0]
        assert 'JOIN employees e' in call_args
        assert 'ORDER BY er.effective_date DESC' in call_args
    
    def test_get_employee_rates_for_specific_employee(self, service, mock_db):
        """Test retrieving rates for specific employee"""
        mock_db.fetchall.return_value = []
        
        service.get_employee_rates(employee_id=1)
        
        call_args = mock_db.fetchall.call_args[0]
        assert 'AND er.employee_id = ?' in call_args[0]
        assert 1 in call_args[1]
    
    def test_get_current_rate(self, service, mock_db):
        """Test getting current rate for employee"""
        rates = [{'hourly_rate': 25.00}]
        mock_db.fetchall.return_value = rates
        
        result = service.get_current_rate(1)
        
        assert result == rates[0]  # Returns the full rate object, not just the hourly_rate
        # get_current_rate calls get_employee_rates which uses fetchall
    
    def test_get_current_rate_not_found(self, service, mock_db):
        """Test getting current rate when none exists"""
        mock_db.fetchall.return_value = []
        
        result = service.get_current_rate(1)
        
        assert result is None
    
    # Test budget allocations
    def test_create_allocation(self, service, mock_db):
        """Test creating budget allocation"""
        mock_db.fetchone.return_value = None  # No existing allocation
        mock_db.insert.return_value = 1
        
        result = service.create_allocation(
            child_id=1,
            employee_id=1,
            period_id=1,
            allocated_hours=40.0,
            notes='Weekly allocation'
        )
        
        assert result == 1
        mock_db.insert.assert_called_once()
        call_args = mock_db.insert.call_args[0]
        assert 'INSERT INTO budget_allocations' in call_args[0]
        assert call_args[1] == (1, 1, 1, 40.0, 'Weekly allocation')
    
    def test_get_allocations(self, service, mock_db):
        """Test getting allocations for period"""
        allocations = [{
            'id': 1,
            'child_name': 'Jane Smith',
            'employee_name': 'John Doe',
            'allocated_hours': 40.0
        }]
        mock_db.fetchall.return_value = allocations
        
        result = service.get_allocations(1)  # Changed method name
        
        assert result == allocations
        call_args = mock_db.fetchall.call_args[0]
        assert 'JOIN children c' in call_args[0]
        assert 'JOIN employees e' in call_args[0]
        assert 'WHERE ba.period_id = ?' in call_args[0]
    
    # Test utilization calculation
    def test_get_budget_utilization(self, service, mock_db):
        """Test budget utilization calculation"""
        # Mock budget
        budget = {
            'id': 1,
            'child_id': 1,
            'budget_amount': 5000.00,
            'budget_hours': 200.0
        }
        
        # Mock no budget report
        mock_db.fetchone.side_effect = [
            budget,  # get_budget_for_period
            None,    # No budget report
            {'total_hours': 150.0, 'shift_count': 20},  # Actual shifts
            {'total_cost': 3750.00}  # Cost calculation
        ]
        
        result = service.get_budget_utilization(1, '2025-01-01', '2025-01-31')
        
        assert result['budget_amount'] == 5000.00
        assert result['budget_hours'] == 200.0
        assert result['actual_hours'] == 150.0
        assert result['actual_cost'] == 3750.00
        assert result['hours_remaining'] == 50.0  # 200 - 150
        assert result['amount_remaining'] == 1250.00  # 5000 - 3750
        assert result['utilization_percent'] == 75.0  # 150/200 * 100
    
    # Test CSV import
    def test_import_budgets_csv(self, service, mock_db):
        """Test importing budgets from CSV"""
        csv_content = """Child Code,Period Start,Period End,Budget Amount,Budget Hours,Notes
JS001,01/01/2025,01/31/2025,5000,200,January budget
JS001,02/01/2025,02/28/2025,5000,200,February budget"""
        
        from io import BytesIO
        file = BytesIO(csv_content.encode('utf-8'))
        
        # Mock child lookup
        mock_db.fetchone.return_value = {'id': 1}
        mock_db.insert.return_value = 1
        
        with patch.object(service, 'create_child_budget', return_value=1) as mock_create:
            result = service.import_budgets_csv(file)
            
            assert result['imported'] == 2  # Changed from imported_count
            assert result['errors'] == []
            assert mock_create.call_count == 2


class TestBudgetServiceIntegration:
    """Integration tests for BudgetService"""
    
    def test_budget_lifecycle(self, test_db, sample_data):
        """Test complete budget lifecycle"""
        service = BudgetService(test_db)
        
        # Create budget
        budget_id = service.create_child_budget(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28',
            budget_amount=5000.00,
            budget_hours=200.0,
            notes='Test budget'
        )
        assert budget_id is not None
        
        # Retrieve budget
        budget = service.get_budget_for_period(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28'
        )
        assert budget is not None
        assert budget['budget_amount'] == 5000.00
        
        # Update budget
        service.update_child_budget(budget_id, budget_amount=6000.00)
        
        # Verify update
        updated = service.get_budget_for_period(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28'
        )
        assert updated['budget_amount'] == 6000.00
        
        # Delete budget
        service.delete_child_budget(budget_id)
        
        # Verify deletion
        deleted = service.get_budget_for_period(
            sample_data['child'].id,
            '2025-02-01',
            '2025-02-28'
        )
        assert deleted is None