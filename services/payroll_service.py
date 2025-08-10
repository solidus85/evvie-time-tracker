from datetime import datetime, timedelta, date

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
    
    def navigate_period(self, period_id, direction):
        """Navigate to the next or previous payroll period"""
        # Get the current period
        current_period = self.db.fetchone(
            "SELECT * FROM payroll_periods WHERE id = ?",
            (period_id,)
        )
        
        if not current_period:
            return None
        
        # Find the next or previous period based on direction
        if direction == 1:  # Next period
            next_period = self.db.fetchone(
                """SELECT * FROM payroll_periods 
                   WHERE start_date > ? 
                   ORDER BY start_date ASC 
                   LIMIT 1""",
                (current_period['end_date'],)
            )
            return next_period
        elif direction == -1:  # Previous period
            prev_period = self.db.fetchone(
                """SELECT * FROM payroll_periods 
                   WHERE end_date < ? 
                   ORDER BY end_date DESC 
                   LIMIT 1""",
                (current_period['start_date'],)
            )
            return prev_period
        else:
            return None
    
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
        query = """SELECT ep.*, e.friendly_name as employee_name, c.name as child_name
                   FROM exclusion_periods ep
                   LEFT JOIN employees e ON ep.employee_id = e.id
                   LEFT JOIN children c ON ep.child_id = c.id"""
        if active_only:
            query += " WHERE ep.active = 1"
        query += " ORDER BY ep.start_date DESC"
        return self.db.fetchall(query)
    
    def get_active_exclusions_for_date(self, date):
        return self.db.fetchall(
            """SELECT * FROM exclusion_periods
               WHERE active = 1 AND start_date <= ? AND end_date >= ?""",
            (date, date)
        )
    
    def create_exclusion_period(self, name, start_date, end_date, start_time=None, end_time=None, 
                               employee_id=None, child_id=None, reason=None):
        if start_date > end_date:
            raise ValueError("End date must be after or equal to start date")
        
        if employee_id and child_id:
            raise ValueError("An exclusion can only be for either an employee or a child, not both")
        
        return self.db.insert(
            """INSERT INTO exclusion_periods 
               (name, start_date, end_date, start_time, end_time, employee_id, child_id, reason) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, start_date, end_date, start_time, end_time, employee_id, child_id, reason)
        )
    
    def update_exclusion_period(self, exclusion_id, name, start_date, end_date, start_time=None, end_time=None, 
                                employee_id=None, child_id=None, reason=None):
        result = self.db.fetchone(
            "SELECT * FROM exclusion_periods WHERE id = ?",
            (exclusion_id,)
        )
        
        if not result:
            return False
        
        if start_date > end_date:
            raise ValueError("End date must be after or equal to start date")
        
        if employee_id and child_id:
            raise ValueError("An exclusion can only be for either an employee or a child, not both")
        
        self.db.execute(
            """UPDATE exclusion_periods 
               SET name = ?, start_date = ?, end_date = ?, start_time = ?, end_time = ?, 
                   employee_id = ?, child_id = ?, reason = ? 
               WHERE id = ?""",
            (name, start_date, end_date, start_time, end_time, employee_id, child_id, reason, exclusion_id)
        )
        return True
    
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
    
    def get_exclusions_for_period(self, start_date, end_date):
        return self.db.fetchall(
            """SELECT ep.*, e.friendly_name as employee_name, c.name as child_name
               FROM exclusion_periods ep
               LEFT JOIN employees e ON ep.employee_id = e.id
               LEFT JOIN children c ON ep.child_id = c.id
               WHERE ep.active = 1 
               AND ((ep.start_date <= ? AND ep.end_date >= ?)
                    OR (ep.start_date <= ? AND ep.end_date >= ?)
                    OR (ep.start_date >= ? AND ep.end_date <= ?))
               ORDER BY ep.start_date""",
            (end_date, start_date, start_date, start_date, start_date, end_date)
        )
    
    def calculate_bulk_dates(self, start_date, end_date, days_of_week, weeks):
        """Calculate all dates that match the pattern within the date range"""
        # If no date range provided, use next 3 months
        if not start_date:
            start_date = date.today()
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if not end_date:
            end_date = start_date + timedelta(days=90)  # Default to 3 months
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start_date > end_date:
            raise ValueError("End date must be after start date")
        
        # Limit to 6 months
        if (end_date - start_date).days > 180:
            raise ValueError("Date range cannot exceed 6 months")
        
        matching_dates = []
        
        # Get all payroll periods that overlap with the date range
        periods = self.db.fetchall(
            """SELECT * FROM payroll_periods 
               WHERE start_date <= ? AND end_date >= ?
               ORDER BY start_date""",
            (end_date.isoformat(), start_date.isoformat())
        )
        
        for period in periods:
            period_start = datetime.strptime(period['start_date'], '%Y-%m-%d').date()
            period_end = datetime.strptime(period['end_date'], '%Y-%m-%d').date()
            
            # Week 1 is first 7 days (Thu-Wed), Week 2 is last 7 days (Thu-Wed)
            week1_end = period_start + timedelta(days=6)
            week2_start = week1_end + timedelta(days=1)
            
            current = max(period_start, start_date)
            period_last = min(period_end, end_date)
            
            while current <= period_last:
                # Check if this day of week is selected
                # Python weekday: 0=Mon, 6=Sun; JavaScript: 0=Sun, 6=Sat
                python_weekday = current.weekday()
                # Convert to JavaScript weekday format
                js_weekday = (python_weekday + 1) % 7
                
                if js_weekday in days_of_week:
                    # Determine which week this date is in
                    if current <= week1_end:
                        week_num = 1
                    else:
                        week_num = 2
                    
                    # Check if this week is selected
                    if weeks == 'both' or (weeks == 'week1' and week_num == 1) or (weeks == 'week2' and week_num == 2):
                        matching_dates.append({
                            'date': current.isoformat(),
                            'week': week_num
                        })
                
                current += timedelta(days=1)
        
        return matching_dates
    
    def create_bulk_exclusions(self, name_pattern, start_date, end_date, days_of_week, weeks,
                              start_time=None, end_time=None, employee_id=None, child_id=None, reason=None):
        """Create multiple exclusion periods based on a pattern"""
        if employee_id and child_id:
            raise ValueError("An exclusion can only be for either an employee or a child, not both")
        
        # Get all matching dates
        dates = self.calculate_bulk_dates(start_date, end_date, days_of_week, weeks)
        
        if not dates:
            raise ValueError("No matching dates found for the specified pattern")
        
        # Day names for naming
        day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        count = 0
        for date_info in dates:
            date_obj = datetime.strptime(date_info['date'], '%Y-%m-%d').date()
            js_weekday = (date_obj.weekday() + 1) % 7
            day_name = day_names[js_weekday]
            
            # Create name with pattern and date
            name = f"{name_pattern} - {day_name} {date_obj.strftime('%-m/%-d')}"
            
            # Create the exclusion for this specific date
            self.db.insert(
                """INSERT INTO exclusion_periods 
                   (name, start_date, end_date, start_time, end_time, employee_id, child_id, reason) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, date_info['date'], date_info['date'], start_time, end_time, employee_id, child_id, reason)
            )
            count += 1
        
        return count