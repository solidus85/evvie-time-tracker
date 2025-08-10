from datetime import datetime, time, timedelta
from services.payroll_service import PayrollService
from services.config_service import ConfigService

class ShiftService:
    def __init__(self, db):
        self.db = db
        self.payroll_service = PayrollService(db)
        self.config_service = ConfigService(db)
    
    def get_shifts(self, start_date=None, end_date=None, employee_id=None, child_id=None):
        query = """
            SELECT s.*, e.friendly_name as employee_name, c.name as child_name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND s.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND s.date <= ?"
            params.append(end_date)
        
        if employee_id:
            query += " AND s.employee_id = ?"
            params.append(employee_id)
        
        if child_id:
            query += " AND s.child_id = ?"
            params.append(child_id)
        
        query += " ORDER BY s.date DESC, s.start_time DESC"
        return self.db.fetchall(query, params)
    
    def get_by_id(self, shift_id):
        return self.db.fetchone(
            """SELECT s.*, e.friendly_name as employee_name, c.name as child_name
               FROM shifts s
               JOIN employees e ON s.employee_id = e.id
               JOIN children c ON s.child_id = c.id
               WHERE s.id = ?""",
            (shift_id,)
        )
    
    def validate_shift(self, employee_id, child_id, date, start_time, end_time, exclude_shift_id=None, allow_overlaps=False):
        warnings = []
        
        if start_time >= end_time:
            raise ValueError("End time must be after start time")
        
        exclusions = self.payroll_service.get_active_exclusions_for_date(date)
        if exclusions:
            warnings.append(f"Date falls within exclusion period: {exclusions[0]['name']}")
        
        overlaps = self.check_overlaps(employee_id, child_id, date, start_time, end_time, exclude_shift_id)
        if overlaps['employee']:
            msg = f"Employee has overlapping shift from {overlaps['employee']['start_time']} to {overlaps['employee']['end_time']}"
            if allow_overlaps:
                warnings.append(msg)
            else:
                raise ValueError(msg)
        if overlaps['child']:
            msg = f"Child has overlapping shift from {overlaps['child']['start_time']} to {overlaps['child']['end_time']}"
            if allow_overlaps:
                warnings.append(msg)
            else:
                raise ValueError(msg)
        
        hour_warning = self.check_hour_limits(employee_id, child_id, date, start_time, end_time, exclude_shift_id)
        if hour_warning:
            warnings.append(hour_warning)
        
        return warnings
    
    def check_overlaps(self, employee_id, child_id, date, start_time, end_time, exclude_shift_id=None):
        query = """
            SELECT * FROM shifts
            WHERE date = ? AND (
                (employee_id = ? AND ((start_time <= ? AND end_time > ?) OR (start_time < ? AND end_time >= ?) OR (start_time >= ? AND end_time <= ?)))
                OR
                (child_id = ? AND ((start_time <= ? AND end_time > ?) OR (start_time < ? AND end_time >= ?) OR (start_time >= ? AND end_time <= ?)))
            )
        """
        params = [
            date,
            employee_id, start_time, start_time, end_time, end_time, start_time, end_time,
            child_id, start_time, start_time, end_time, end_time, start_time, end_time
        ]
        
        if exclude_shift_id:
            query += " AND id != ?"
            params.append(exclude_shift_id)
        
        overlaps = self.db.fetchall(query, params)
        
        result = {'employee': None, 'child': None}
        for overlap in overlaps:
            if overlap['employee_id'] == employee_id:
                result['employee'] = overlap
            if overlap['child_id'] == child_id:
                result['child'] = overlap
        
        return result
    
    def check_hour_limits(self, employee_id, child_id, date, start_time, end_time, exclude_shift_id=None):
        limit = self.config_service.get_hour_limit(employee_id, child_id)
        if not limit:
            return None
        
        period = self.payroll_service.get_period_for_date(date)
        if not period:
            return None
        
        # Determine which week this shift falls into
        period_start = datetime.strptime(period['start_date'], "%Y-%m-%d")
        shift_date = datetime.strptime(date, "%Y-%m-%d")
        days_from_start = (shift_date - period_start).days
        week_number = 1 if days_from_start < 7 else 2
        
        # Calculate week boundaries
        if week_number == 1:
            week_start = period['start_date']
            week_end_date = period_start + datetime.timedelta(days=6)
            week_end = week_end_date.strftime("%Y-%m-%d")
        else:
            week_start_date = period_start + datetime.timedelta(days=7)
            week_start = week_start_date.strftime("%Y-%m-%d")
            week_end = period['end_date']
        
        # Calculate existing hours for this week
        existing_hours = self.calculate_period_hours(
            employee_id, child_id, week_start, week_end, exclude_shift_id
        )
        
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
        new_hours = (end_dt - start_dt).total_seconds() / 3600
        
        total_hours = existing_hours + new_hours
        
        if total_hours > limit['max_hours_per_week']:
            return f"Week {week_number} hours ({total_hours:.1f}) exceeds weekly limit ({limit['max_hours_per_week']:.1f}) for this employee/child pair"
        elif limit['alert_threshold'] and total_hours > limit['alert_threshold']:
            return f"Week {week_number} hours ({total_hours:.1f}) exceeds alert threshold ({limit['alert_threshold']:.1f}) for this employee/child pair"
        
        return None
    
    def calculate_period_hours(self, employee_id, child_id, start_date, end_date, exclude_shift_id=None):
        query = """
            SELECT SUM((julianday(date || ' ' || end_time) - julianday(date || ' ' || start_time)) * 24) as total_hours
            FROM shifts
            WHERE employee_id = ? AND child_id = ? AND date >= ? AND date <= ?
        """
        params = [employee_id, child_id, start_date, end_date]
        
        if exclude_shift_id:
            query += " AND id != ?"
            params.append(exclude_shift_id)
        
        result = self.db.fetchone(query, params)
        return result['total_hours'] or 0
    
    def create(self, employee_id, child_id, date, start_time, end_time, service_code=None, status='new', is_imported=False):
        return self.db.insert(
            """INSERT INTO shifts (employee_id, child_id, date, start_time, end_time, service_code, status, is_imported)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (employee_id, child_id, date, start_time, end_time, service_code, status, is_imported)
        )
    
    def update(self, shift_id, data):
        shift = self.get_by_id(shift_id)
        if not shift or shift['is_imported']:
            return False
        
        updates = []
        params = []
        
        for field in ['employee_id', 'child_id', 'date', 'start_time', 'end_time', 'service_code', 'status']:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
        
        if not updates:
            return True
        
        params.append(shift_id)
        query = f"UPDATE shifts SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, params)
        return True
    
    def delete(self, shift_id):
        shift = self.get_by_id(shift_id)
        if not shift or shift['is_imported']:
            return False
        
        self.db.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        return True