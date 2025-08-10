from datetime import datetime, date
import csv
from io import StringIO

class BudgetService:
    def __init__(self, db):
        self.db = db
    
    # Child Budget Management
    def get_child_budgets(self, child_id=None, active_only=True):
        """Get budget records for children"""
        query = """
            SELECT cb.*, c.name as child_name, c.code as child_code
            FROM child_budgets cb
            JOIN children c ON cb.child_id = c.id
            WHERE 1=1
        """
        params = []
        
        if child_id:
            query += " AND cb.child_id = ?"
            params.append(child_id)
        
        if active_only:
            query += " AND cb.period_end >= date('now')"
        
        query += " ORDER BY cb.period_start DESC"
        return self.db.fetchall(query, params)
    
    def get_budget_for_period(self, child_id, period_start, period_end):
        """Get budget for a specific child and period"""
        return self.db.fetchone(
            """SELECT * FROM child_budgets 
               WHERE child_id = ? AND period_start = ? AND period_end = ?""",
            (child_id, period_start, period_end)
        )
    
    def create_child_budget(self, child_id, period_start, period_end, 
                           budget_amount=None, budget_hours=None, notes=None):
        """Create or update a budget record for a child"""
        existing = self.get_budget_for_period(child_id, period_start, period_end)
        
        if existing:
            return self.update_child_budget(
                existing['id'], budget_amount, budget_hours, notes
            )
        
        return self.db.insert(
            """INSERT INTO child_budgets 
               (child_id, period_start, period_end, budget_amount, budget_hours, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (child_id, period_start, period_end, budget_amount, budget_hours, notes)
        )
    
    def update_child_budget(self, budget_id, budget_amount=None, 
                           budget_hours=None, notes=None):
        """Update an existing budget record"""
        self.db.execute(
            """UPDATE child_budgets 
               SET budget_amount = ?, budget_hours = ?, notes = ?, 
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (budget_amount, budget_hours, notes, budget_id)
        )
        return budget_id
    
    def delete_child_budget(self, budget_id):
        """Delete a budget record"""
        self.db.execute("DELETE FROM child_budgets WHERE id = ?", (budget_id,))
    
    # Employee Rate Management
    def get_employee_rates(self, employee_id=None, as_of_date=None):
        """Get employee hourly rates"""
        if as_of_date is None:
            as_of_date = date.today().isoformat()
        
        query = """
            SELECT er.*, e.friendly_name as employee_name
            FROM employee_rates er
            JOIN employees e ON er.employee_id = e.id
            WHERE er.effective_date <= ?
            AND (er.end_date IS NULL OR er.end_date >= ?)
        """
        params = [as_of_date, as_of_date]
        
        if employee_id:
            query += " AND er.employee_id = ?"
            params.append(employee_id)
        
        query += " ORDER BY er.effective_date DESC"
        return self.db.fetchall(query, params)
    
    def get_current_rate(self, employee_id):
        """Get current hourly rate for an employee"""
        rates = self.get_employee_rates(employee_id)
        return rates[0] if rates else None
    
    def create_employee_rate(self, employee_id, hourly_rate, effective_date, 
                            end_date=None, notes=None):
        """Create a new rate record for an employee"""
        # End any existing open-ended rate records
        self.db.execute(
            """UPDATE employee_rates 
               SET end_date = date(?, '-1 day')
               WHERE employee_id = ? AND end_date IS NULL
               AND effective_date < ?""",
            (effective_date, employee_id, effective_date)
        )
        
        return self.db.insert(
            """INSERT INTO employee_rates 
               (employee_id, hourly_rate, effective_date, end_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, hourly_rate, effective_date, end_date, notes)
        )
    
    def update_employee_rate(self, rate_id, hourly_rate, end_date=None, notes=None):
        """Update an existing rate record"""
        self.db.execute(
            """UPDATE employee_rates 
               SET hourly_rate = ?, end_date = ?, notes = ?
               WHERE id = ?""",
            (hourly_rate, end_date, notes, rate_id)
        )
    
    # Budget Allocation Management
    def get_allocations(self, period_id, child_id=None, employee_id=None):
        """Get budget allocations for a period"""
        query = """
            SELECT ba.*, c.name as child_name, e.friendly_name as employee_name,
                   pp.start_date, pp.end_date
            FROM budget_allocations ba
            JOIN children c ON ba.child_id = c.id
            JOIN employees e ON ba.employee_id = e.id
            JOIN payroll_periods pp ON ba.period_id = pp.id
            WHERE ba.period_id = ?
        """
        params = [period_id]
        
        if child_id:
            query += " AND ba.child_id = ?"
            params.append(child_id)
        
        if employee_id:
            query += " AND ba.employee_id = ?"
            params.append(employee_id)
        
        return self.db.fetchall(query, params)
    
    def create_allocation(self, child_id, employee_id, period_id, 
                         allocated_hours, notes=None):
        """Create or update an allocation"""
        existing = self.db.fetchone(
            """SELECT id FROM budget_allocations
               WHERE child_id = ? AND employee_id = ? AND period_id = ?""",
            (child_id, employee_id, period_id)
        )
        
        if existing:
            self.db.execute(
                """UPDATE budget_allocations 
                   SET allocated_hours = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (allocated_hours, notes, existing['id'])
            )
            return existing['id']
        
        return self.db.insert(
            """INSERT INTO budget_allocations 
               (child_id, employee_id, period_id, allocated_hours, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (child_id, employee_id, period_id, allocated_hours, notes)
        )
    
    # Budget Analysis
    def get_budget_utilization(self, child_id, period_start, period_end):
        """Calculate budget utilization for a child in a period"""
        budget = self.get_budget_for_period(child_id, period_start, period_end)
        if not budget:
            return None
        
        # Get actual hours worked
        actual = self.db.fetchone(
            """SELECT SUM((julianday(date || ' ' || end_time) - 
                          julianday(date || ' ' || start_time)) * 24) as total_hours,
                      COUNT(*) as shift_count
               FROM shifts
               WHERE child_id = ? AND date >= ? AND date <= ?""",
            (child_id, period_start, period_end)
        )
        
        # Calculate costs if rates are available
        cost_query = """
            SELECT SUM(
                (julianday(s.date || ' ' || s.end_time) - 
                 julianday(s.date || ' ' || s.start_time)) * 24 * 
                COALESCE(er.hourly_rate, e.hourly_rate, 0)
            ) as total_cost
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN employee_rates er ON er.employee_id = e.id
                AND er.effective_date <= s.date
                AND (er.end_date IS NULL OR er.end_date >= s.date)
            WHERE s.child_id = ? AND s.date >= ? AND s.date <= ?
        """
        cost_result = self.db.fetchone(cost_query, (child_id, period_start, period_end))
        
        return {
            'budget_amount': budget['budget_amount'],
            'budget_hours': budget['budget_hours'],
            'actual_hours': actual['total_hours'] or 0,
            'actual_cost': cost_result['total_cost'] or 0,
            'shift_count': actual['shift_count'] or 0,
            'hours_remaining': (budget['budget_hours'] or 0) - (actual['total_hours'] or 0),
            'amount_remaining': (budget['budget_amount'] or 0) - (cost_result['total_cost'] or 0),
            'utilization_percent': (
                ((actual['total_hours'] or 0) / budget['budget_hours'] * 100) 
                if budget['budget_hours'] else 0
            )
        }
    
    def import_budgets_csv(self, file):
        """Import budget data from CSV file"""
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        
        imported = 0
        errors = []
        
        for i, row in enumerate(reader, 1):
            try:
                # Expected columns: Child Code, Period Start, Period End, Budget Amount, Budget Hours
                child = self.db.fetchone(
                    "SELECT id FROM children WHERE code = ?",
                    (row.get('Child Code', '').strip(),)
                )
                
                if not child:
                    errors.append(f"Row {i}: Child code '{row.get('Child Code')}' not found")
                    continue
                
                period_start = datetime.strptime(
                    row['Period Start'], '%m/%d/%Y'
                ).strftime('%Y-%m-%d')
                period_end = datetime.strptime(
                    row['Period End'], '%m/%d/%Y'
                ).strftime('%Y-%m-%d')
                
                budget_amount = float(row['Budget Amount']) if row.get('Budget Amount') else None
                budget_hours = float(row['Budget Hours']) if row.get('Budget Hours') else None
                
                self.create_child_budget(
                    child['id'], period_start, period_end,
                    budget_amount, budget_hours,
                    row.get('Notes', '')
                )
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
        
        return {'imported': imported, 'errors': errors}