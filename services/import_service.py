import csv
import re
from datetime import datetime
from io import StringIO
from services.employee_service import EmployeeService
from services.child_service import ChildService
from services.shift_service import ShiftService

class ImportService:
    def __init__(self, db):
        self.db = db
        self.employee_service = EmployeeService(db)
        self.child_service = ChildService(db)
        self.shift_service = ShiftService(db)
    
    def parse_csv_row(self, row):
        date_str = row['Date']
        date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
        
        consumer_match = re.match(r'(.+?)\s*\(([A-Z0-9]+)\)', row['Consumer'])
        child_name = consumer_match.group(1) if consumer_match else row['Consumer']
        child_code = consumer_match.group(2) if consumer_match else None
        
        employee_match = re.match(r'(.+?)\s*\(([A-Z0-9]+)\)', row['Employee'])
        employee_name = employee_match.group(1) if employee_match else row['Employee']
        employee_code = employee_match.group(2) if employee_match else None
        
        start_match = re.match(r'Start:\s*(.+)', row['Start Time'])
        start_time_str = start_match.group(1) if start_match else row['Start Time']
        start_time = datetime.strptime(start_time_str, '%I:%M %p').strftime('%H:%M:%S')
        
        end_match = re.match(r'End:\s*(.+)', row['End Time'])
        end_time_str = end_match.group(1) if end_match else row['End Time']
        end_time = datetime.strptime(end_time_str, '%I:%M %p').strftime('%H:%M:%S')
        
        # Handle special case where 12:00 AM means end of day
        if end_time == '00:00:00':
            end_time = '23:59:59'
        
        return {
            'date': date,
            'child_name': child_name,
            'child_code': child_code,
            'employee_name': employee_name,
            'employee_code': employee_code,
            'start_time': start_time,
            'end_time': end_time,
            'service_code': row.get('Service Code'),
            'status': row.get('Status', 'imported')
        }
    
    def validate_csv(self, file):
        try:
            content = file.read().decode('utf-8')
            file.seek(0)
            
            reader = csv.DictReader(StringIO(content))
            required_columns = ['Date', 'Consumer', 'Employee', 'Start Time', 'End Time']
            
            if not all(col in reader.fieldnames for col in required_columns):
                return {
                    'valid': False,
                    'errors': [f"Missing required columns. Required: {required_columns}"],
                    'warnings': [],
                    'rows': 0
                }
            
            errors = []
            warnings = []
            row_count = 0
            
            for i, row in enumerate(reader, 1):
                row_count = i
                try:
                    parsed = self.parse_csv_row(row)
                    
                    if not parsed['child_code']:
                        warnings.append(f"Row {i}: No code found for child '{parsed['child_name']}'")
                    if not parsed['employee_code']:
                        warnings.append(f"Row {i}: No code found for employee '{parsed['employee_name']}'")
                    
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'rows': row_count
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Failed to parse CSV: {str(e)}"],
                'warnings': [],
                'rows': 0
            }
    
    def import_csv(self, file):
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        
        imported = 0
        duplicates = 0
        replaced = 0  # Track replaced manual shifts
        errors = []
        warnings = []
        
        for i, row in enumerate(reader, 1):
            try:
                parsed = self.parse_csv_row(row)
                
                employee = self.employee_service.get_by_system_name(parsed['employee_name'])
                if not employee:
                    employee_id = self.employee_service.create(
                        friendly_name=parsed['employee_name'],
                        system_name=parsed['employee_name']
                    )
                else:
                    employee_id = employee['id']
                
                child = self.child_service.get_by_code(parsed['child_code']) if parsed['child_code'] else None
                if not child:
                    child = self.child_service.get_by_code(parsed['child_name'])
                
                if not child:
                    child_id = self.child_service.create(
                        name=parsed['child_name'],
                        code=parsed['child_code'] or parsed['child_name']
                    )
                else:
                    child_id = child['id']
                
                # Check for existing shift with matching employee, child, date, and times
                existing = self.db.fetchone(
                    """SELECT * FROM shifts
                       WHERE employee_id = ? AND child_id = ? AND date = ? 
                       AND start_time = ? AND end_time = ?""",
                    (employee_id, child_id, parsed['date'], parsed['start_time'], parsed['end_time'])
                )
                
                if existing:
                    if not existing['is_imported']:
                        # Delete the manual shift - imported takes precedence
                        self.shift_service.delete(existing['id'])
                        replaced += 1
                        # Continue to import the new shift
                    else:
                        # Already imported, skip as duplicate
                        duplicates += 1
                        continue
                
                try:
                    shift_warnings = self.shift_service.validate_shift(
                        employee_id=employee_id,
                        child_id=child_id,
                        date=parsed['date'],
                        start_time=parsed['start_time'],
                        end_time=parsed['end_time'],
                        allow_overlaps=True  # Allow overlaps for imports from source of truth
                    )
                    
                    if shift_warnings:
                        warnings.extend([f"Row {i}: {w}" for w in shift_warnings])
                    
                except ValueError as e:
                    # Only skip if there's a critical error (like invalid time)
                    errors.append(f"Row {i}: {str(e)}")
                    continue
                
                self.shift_service.create(
                    employee_id=employee_id,
                    child_id=child_id,
                    date=parsed['date'],
                    start_time=parsed['start_time'],
                    end_time=parsed['end_time'],
                    service_code=parsed['service_code'],
                    status=parsed['status'],
                    is_imported=True
                )
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
        
        return {
            'imported': imported,
            'duplicates': duplicates,
            'replaced': replaced,
            'errors': errors,
            'warnings': warnings
        }