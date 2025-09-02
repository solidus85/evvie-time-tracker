import csv
import re
import json
from datetime import datetime
from io import StringIO
from services.employee_service import EmployeeService
from services.child_service import ChildService
from services.shift_service import ShiftService
from services.config_service import ConfigService

class ImportService:
    def __init__(self, db):
        self.db = db
        self.employee_service = EmployeeService(db)
        self.child_service = ChildService(db)
        self.shift_service = ShiftService(db)
        self.config_service = ConfigService(db)
    
    def _normalize_header(self, name):
        if name is None:
            return ''
        s = name.strip().lower()
        if s and s[0] == '\ufeff':
            s = s.lstrip('\ufeff')
        synonyms = {
            'consumer name': 'consumer',
            'child': 'consumer',
            'child name': 'consumer',
            'client': 'consumer',
            'client name': 'consumer',
            'employee name': 'employee',
            'staff': 'employee',
            'start': 'start time',
            'start_time': 'start time',
            'end': 'end time',
            'end_time': 'end time',
            'service': 'service code'
        }
        return synonyms.get(s, s)

    def _normalize_row(self, row):
        return {self._normalize_header(k): v for k, v in row.items()}
    
    def parse_csv_row(self, row):
        # Expect normalized lowercase keys
        date_str = row['date']
        date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
        
        # Extract child name and optional code from parentheses
        consumer_match_generic = re.match(r"(.+?)\s*\((.+?)\)\s*$", row['consumer'])
        if consumer_match_generic:
            child_name = consumer_match_generic.group(1).strip()
            code_candidate = consumer_match_generic.group(2).strip()
            child_code = code_candidate if re.fullmatch(r"[A-Z0-9]+", code_candidate) else None
        else:
            child_name = row['consumer']
            child_code = None
        
        # Extract employee name; treat any parenthetical suffix as non-canonical display and drop it
        employee_generic = re.match(r"(.+?)\s*\((.+?)\)\s*$", row['employee'])
        if employee_generic:
            employee_name = employee_generic.group(1).strip()
            code_candidate = employee_generic.group(2).strip()
            employee_code = code_candidate if re.fullmatch(r"[A-Z0-9]+", code_candidate) else None
        else:
            employee_name = row['employee']
            employee_code = None
        
        start_match = re.match(r'Start:\s*(.+)', row['start time'])
        start_time_str = start_match.group(1) if start_match else row['start time']
        start_time = datetime.strptime(start_time_str, '%I:%M %p').strftime('%H:%M:%S')
        
        end_match = re.match(r'End:\s*(.+)', row['end time'])
        end_time_str = end_match.group(1) if end_match else row['end time']
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
            'service_code': row.get('service code'),
            'status': row.get('status', 'imported')
        }
    
    def validate_csv(self, file):
        try:
            content = file.read().decode('utf-8')
            file.seek(0)
            
            reader = csv.DictReader(StringIO(content))
            if not reader.fieldnames:
                return {
                    'valid': False,
                    'errors': ["CSV appears to have no header row"],
                    'warnings': [],
                    'rows': 0
                }
            normalized_fields = [self._normalize_header(h) for h in reader.fieldnames]
            required_columns = ['date', 'consumer', 'employee', 'start time', 'end time']
            missing = [c for c in required_columns if c not in normalized_fields]
            if missing:
                return {
                    'valid': False,
                    'errors': [f"Missing required columns: {', '.join(missing)}. Found: {', '.join(normalized_fields)}"],
                    'warnings': [],
                    'rows': 0
                }

            errors = []
            warnings = []

            # Compare against previously seen header schema and error on changes
            try:
                prev_schema = self.config_service.get_setting('import_csv_headers')
                if prev_schema:
                    prev = json.loads(prev_schema)
                    prev_set, cur_set = set(prev), set(normalized_fields)
                    added = cur_set - prev_set
                    removed = prev_set - cur_set
                    if added or removed:
                        msg_parts = []
                        if added:
                            msg_parts.append(f"added: {', '.join(sorted(added))}")
                        if removed:
                            msg_parts.append(f"removed: {', '.join(sorted(removed))}")
                        errors.append("CSV header schema changed since last import (" + "; ".join(msg_parts) + ")")
                else:
                    # No baseline recorded yet – treat as baseline on first import
                    pass
            except Exception:
                # Non-fatal
                pass
            row_count = 0
            
            for i, row in enumerate(reader, 1):
                row_count = i
                try:
                    parsed = self.parse_csv_row(self._normalize_row(row))
                    
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
        baseline_set = False
        normalized_fields = []

        # Fail fast if header schema changed vs. previous
        try:
            if reader.fieldnames:
                normalized_fields = [self._normalize_header(h) for h in reader.fieldnames]
                prev_schema = self.config_service.get_setting('import_csv_headers')
                if prev_schema:
                    prev = json.loads(prev_schema)
                    prev_set, cur_set = set(prev), set(normalized_fields)
                    added = cur_set - prev_set
                    removed = prev_set - cur_set
                    if added or removed:
                        msg_parts = []
                        if added:
                            msg_parts.append(f"added: {', '.join(sorted(added))}")
                        if removed:
                            msg_parts.append(f"removed: {', '.join(sorted(removed))}")
                        return {
                            'imported': 0,
                            'duplicates': 0,
                            'replaced': 0,
                            'errors': ["CSV header schema changed since last import (" + "; ".join(msg_parts) + ")"],
                            'warnings': []
                        }
                else:
                    # No baseline recorded yet – allow and set after import (and inform user)
                    baseline_set = True
        except Exception:
            pass
        
        for i, row in enumerate(reader, 1):
            try:
                parsed = self.parse_csv_row(self._normalize_row(row))
                
                # Resolve employee by system_name or alias (slug)
                employee = self.employee_service.get_by_alias(parsed['employee_name'])
                if not employee:
                    # Create with canonical slug as system_name
                    slug = self.employee_service._slugify(parsed['employee_name'])
                    employee_id = self.employee_service.create(
                        friendly_name=parsed['employee_name'],
                        system_name=slug
                    )
                else:
                    employee_id = employee['id']
                    # Ensure we remember this alias if it wasn't recorded
                    try:
                        self.employee_service.ensure_alias(employee_id, parsed['employee_name'], source='import')
                    except Exception:
                        pass
                
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
                        # Convert the existing manual shift to imported and align details
                        try:
                            self.db.execute(
                                """UPDATE shifts 
                                       SET is_imported = 1,
                                           status = COALESCE(?, status),
                                           service_code = COALESCE(?, service_code),
                                           start_time = ?,
                                           end_time = ?
                                     WHERE id = ?""",
                                (parsed['status'], parsed['service_code'], parsed['start_time'], parsed['end_time'], existing['id'])
                            )
                            replaced += 1
                        except Exception as e:
                            # Fallback: delete and re-insert if update fails for any reason
                            self.shift_service.delete(existing['id'])
                            replaced += 1
                            # proceed to create below
                        else:
                            # Update done, no need to insert a new row
                            continue
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
        
        # Update stored header schema baseline after processing
        try:
            if reader.fieldnames:
                if not normalized_fields:
                    normalized_fields = [self._normalize_header(h) for h in reader.fieldnames]
                self.config_service.set_setting('import_csv_headers', json.dumps(normalized_fields))
                if baseline_set:
                    warnings.append("CSV header baseline set to: " + ", ".join(normalized_fields))
        except Exception:
            pass

        return {
            'imported': imported,
            'duplicates': duplicates,
            'replaced': replaced,
            'errors': errors,
            'warnings': warnings
        }
