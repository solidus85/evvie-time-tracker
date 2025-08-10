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
        # First check child_budgets table
        budget = self.db.fetchone(
            """SELECT * FROM child_budgets 
               WHERE child_id = ? AND period_start = ? AND period_end = ?""",
            (child_id, period_start, period_end)
        )
        
        if budget:
            return budget
        
        # If no manual budget found, check budget_reports for overlapping period
        # Find the most recent report that covers this period
        report = self.db.fetchone(
            """SELECT * FROM budget_reports 
               WHERE child_id = ? 
               AND period_start <= ? 
               AND period_end >= ?
               ORDER BY created_at DESC
               LIMIT 1""",
            (child_id, period_end, period_start)
        )
        
        if report:
            # Convert budget report to budget format
            # Calculate hours from dollars using average rate from report data
            import json
            try:
                report_data = json.loads(report['report_data'])
                
                # Calculate average hourly rate from employee spending
                total_hours = 0
                total_amount = 0
                
                if 'employee_spending_summary' in report_data:
                    for emp_name, emp_data in report_data['employee_spending_summary'].items():
                        total_hours += emp_data.get('total_hours', 0)
                        total_amount += emp_data.get('total_amount', 0)
                
                # Use average rate to convert budget to hours
                avg_rate = (total_amount / total_hours) if total_hours > 0 else 25.0  # Default $25/hr
                
                budget_hours = report['total_budgeted'] / avg_rate if report['total_budgeted'] else 0
                
                return {
                    'id': None,  # Indicate this is from report, not manual budget
                    'child_id': child_id,
                    'period_start': report['period_start'],
                    'period_end': report['period_end'],
                    'budget_amount': report['total_budgeted'],
                    'budget_hours': round(budget_hours, 2),
                    'notes': f"From PDF report dated {report['report_date']}"
                }
            except (json.JSONDecodeError, KeyError):
                pass
        
        return None
    
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
        
        # Check if we have a budget report for this period
        report = self.db.fetchone(
            """SELECT * FROM budget_reports 
               WHERE child_id = ? 
               AND period_start <= ? 
               AND period_end >= ?
               ORDER BY report_date DESC
               LIMIT 1""",
            (child_id, period_end, period_start)
        )
        
        total_hours_used = 0
        total_cost_used = 0
        
        if report:
            # Use the spending from the PDF report as the baseline
            import json
            try:
                report_data = json.loads(report['report_data'])
                
                # Calculate average hourly rate from the report
                total_report_hours = 0
                total_report_amount = 0
                
                if 'employee_spending_summary' in report_data:
                    for emp_name, emp_data in report_data['employee_spending_summary'].items():
                        total_report_hours += emp_data.get('total_hours', 0)
                        total_report_amount += emp_data.get('total_amount', 0)
                
                # Use average rate to convert spent amount to hours
                avg_rate = (total_report_amount / total_report_hours) if total_report_hours > 0 else 25.0
                
                # The report shows cumulative spending up to the report date
                total_cost_used = report['total_spent'] or 0
                total_hours_used = total_cost_used / avg_rate if avg_rate > 0 else 0
                
                # Now add any manual shifts that occurred AFTER the report date
                # This ensures we don't double-count hours
                additional_shifts = self.db.fetchone(
                    """SELECT SUM((julianday(date || ' ' || end_time) - 
                                  julianday(date || ' ' || start_time)) * 24) as total_hours
                       FROM shifts
                       WHERE child_id = ? AND date > ? AND date <= ?""",
                    (child_id, report['report_date'], period_end)
                )
                
                if additional_shifts and additional_shifts['total_hours']:
                    total_hours_used += additional_shifts['total_hours']
                    # Estimate cost for additional shifts
                    total_cost_used += additional_shifts['total_hours'] * avg_rate
                    
            except (json.JSONDecodeError, KeyError):
                # Fallback to manual shifts only if report parsing fails
                pass
        
        # If no report or parsing failed, use manual shifts only
        if total_hours_used == 0:
            actual = self.db.fetchone(
                """SELECT SUM((julianday(date || ' ' || end_time) - 
                              julianday(date || ' ' || start_time)) * 24) as total_hours,
                          COUNT(*) as shift_count
                   FROM shifts
                   WHERE child_id = ? AND date >= ? AND date <= ?""",
                (child_id, period_start, period_end)
            )
            
            total_hours_used = actual['total_hours'] or 0
            
            # Calculate costs if rates are available
            cost_query = """
                SELECT SUM(
                    (julianday(s.date || ' ' || s.end_time) - 
                     julianday(s.date || ' ' || s.start_time)) * 24 * 
                    COALESCE(er.hourly_rate, e.hourly_rate, 25)
                ) as total_cost
                FROM shifts s
                JOIN employees e ON s.employee_id = e.id
                LEFT JOIN employee_rates er ON er.employee_id = e.id
                    AND er.effective_date <= s.date
                    AND (er.end_date IS NULL OR er.end_date >= s.date)
                WHERE s.child_id = ? AND s.date >= ? AND s.date <= ?
            """
            cost_result = self.db.fetchone(cost_query, (child_id, period_start, period_end))
            total_cost_used = cost_result['total_cost'] or 0
        
        return {
            'budget_amount': budget['budget_amount'],
            'budget_hours': budget['budget_hours'],
            'actual_hours': round(total_hours_used, 2),
            'actual_cost': round(total_cost_used, 2),
            'shift_count': 0,  # Not tracking this anymore since we use report data
            'hours_remaining': round((budget['budget_hours'] or 0) - total_hours_used, 2),
            'amount_remaining': round((budget['budget_amount'] or 0) - total_cost_used, 2),
            'utilization_percent': round((total_hours_used / budget['budget_hours'] * 100) if budget['budget_hours'] else 0, 2)
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