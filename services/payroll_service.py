from datetime import datetime, timedelta

class PayrollService:
    def __init__(self, db):
        self.db = db
    
    def get_all_periods(self):
        return self.db.fetchall(
            "SELECT * FROM payroll_periods ORDER BY start_date DESC"
        )
    
    def get_current_period(self):
        today = datetime.now().date().isoformat()
        return self.db.fetchone(
            "SELECT * FROM payroll_periods WHERE start_date <= ? AND end_date >= ?",
            (today, today)
        )
    
    def get_period_for_date(self, date):
        return self.db.fetchone(
            "SELECT * FROM payroll_periods WHERE start_date <= ? AND end_date >= ?",
            (date, date)
        )
    
    def configure_periods(self, anchor_date):
        self.db.execute("DELETE FROM payroll_periods")
        
        self.db.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES ('payroll_anchor_date', ?)",
            (anchor_date,)
        )
        
        start = datetime.strptime(anchor_date, '%Y-%m-%d').date()
        current_date = datetime.now().date()
        
        while start < current_date - timedelta(days=365):
            start += timedelta(days=14)
        
        start -= timedelta(days=14 * 10)
        
        for _ in range(30):
            end = start + timedelta(days=13)
            self.db.insert(
                "INSERT INTO payroll_periods (start_date, end_date) VALUES (?, ?)",
                (start.isoformat(), end.isoformat())
            )
            start = end + timedelta(days=1)
    
    def get_period_summary(self, period_id):
        period = self.db.fetchone(
            "SELECT * FROM payroll_periods WHERE id = ?",
            (period_id,)
        )
        
        if not period:
            return None
        
        shifts = self.db.fetchall(
            """SELECT s.*, e.friendly_name as employee_name, c.name as child_name,
                      (julianday(date || ' ' || end_time) - julianday(date || ' ' || start_time)) * 24 as hours
               FROM shifts s
               JOIN employees e ON s.employee_id = e.id
               JOIN children c ON s.child_id = c.id
               WHERE s.date >= ? AND s.date <= ?
               ORDER BY s.date, s.start_time""",
            (period['start_date'], period['end_date'])
        )
        
        total_hours = sum(shift['hours'] for shift in shifts)
        imported_count = sum(1 for shift in shifts if shift['is_imported'])
        manual_count = len(shifts) - imported_count
        
        employee_hours = {}
        child_hours = {}
        
        for shift in shifts:
            emp_key = f"{shift['employee_id']}_{shift['employee_name']}"
            child_key = f"{shift['child_id']}_{shift['child_name']}"
            
            if emp_key not in employee_hours:
                employee_hours[emp_key] = 0
            if child_key not in child_hours:
                child_hours[child_key] = 0
            
            employee_hours[emp_key] += shift['hours']
            child_hours[child_key] += shift['hours']
        
        return {
            'period': dict(period),
            'total_shifts': len(shifts),
            'imported_shifts': imported_count,
            'manual_shifts': manual_count,
            'total_hours': round(total_hours, 2),
            'employee_hours': {k: round(v, 2) for k, v in employee_hours.items()},
            'child_hours': {k: round(v, 2) for k, v in child_hours.items()}
        }
    
    def get_exclusion_periods(self, active_only=False):
        query = "SELECT * FROM exclusion_periods"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY start_date DESC"
        return self.db.fetchall(query)
    
    def get_active_exclusions_for_date(self, date):
        return self.db.fetchall(
            """SELECT * FROM exclusion_periods
               WHERE active = 1 AND start_date <= ? AND end_date >= ?""",
            (date, date)
        )
    
    def create_exclusion_period(self, name, start_date, end_date, reason=None):
        if start_date > end_date:
            raise ValueError("End date must be after or equal to start date")
        
        return self.db.insert(
            "INSERT INTO exclusion_periods (name, start_date, end_date, reason) VALUES (?, ?, ?, ?)",
            (name, start_date, end_date, reason)
        )
    
    def deactivate_exclusion_period(self, exclusion_id):
        result = self.db.fetchone(
            "SELECT * FROM exclusion_periods WHERE id = ?",
            (exclusion_id,)
        )
        
        if not result:
            return False
        
        self.db.execute(
            "UPDATE exclusion_periods SET active = 0 WHERE id = ?",
            (exclusion_id,)
        )
        return True