import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os

class Database:
    def __init__(self, db_path='evvie_time_tracker.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    friendly_name TEXT NOT NULL,
                    system_name TEXT NOT NULL UNIQUE,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS employee_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    alias TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                );
                
                CREATE TABLE IF NOT EXISTS children (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL UNIQUE,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS shifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    child_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    service_code TEXT,
                    status TEXT,
                    is_imported BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (child_id) REFERENCES children(id),
                    CHECK (end_time > start_time)
                );
                
                CREATE UNIQUE INDEX IF NOT EXISTS idx_shift_unique 
                ON shifts(employee_id, child_id, date, start_time, end_time);
                
                CREATE INDEX IF NOT EXISTS idx_shift_employee_date 
                ON shifts(employee_id, date);
                
                CREATE INDEX IF NOT EXISTS idx_shift_child_date 
                ON shifts(child_id, date);
                
                CREATE TABLE IF NOT EXISTS payroll_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_date DATE NOT NULL UNIQUE,
                    end_date DATE NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS exclusion_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    start_time TIME,
                    end_time TIME,
                    employee_id INTEGER,
                    child_id INTEGER,
                    reason TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (child_id) REFERENCES children(id),
                    CHECK ((employee_id IS NOT NULL AND child_id IS NULL) OR 
                           (employee_id IS NULL AND child_id IS NOT NULL) OR
                           (employee_id IS NULL AND child_id IS NULL))
                );
                
                CREATE TABLE IF NOT EXISTS hour_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    child_id INTEGER NOT NULL,
                    max_hours_per_week REAL NOT NULL,
                    alert_threshold REAL,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (child_id) REFERENCES children(id),
                    UNIQUE(employee_id, child_id)
                );
                
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Budget tracking tables
                CREATE TABLE IF NOT EXISTS child_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER NOT NULL,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    budget_amount REAL,
                    budget_hours REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (child_id) REFERENCES children(id),
                    UNIQUE(child_id, period_start, period_end)
                );
                
                CREATE TABLE IF NOT EXISTS employee_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    hourly_rate REAL NOT NULL,
                    effective_date DATE NOT NULL,
                    end_date DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                );
                
                CREATE TABLE IF NOT EXISTS budget_allocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER NOT NULL,
                    employee_id INTEGER NOT NULL,
                    period_id INTEGER NOT NULL,
                    allocated_hours REAL NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (child_id) REFERENCES children(id),
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (period_id) REFERENCES payroll_periods(id),
                    UNIQUE(child_id, employee_id, period_id)
                );
                
                CREATE TABLE IF NOT EXISTS budget_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER,
                    report_date DATE NOT NULL,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    total_budgeted REAL,
                    total_spent REAL,
                    remaining_balance REAL,
                    utilization_percent REAL,
                    report_data JSON,
                    pdf_filename TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (child_id) REFERENCES children(id)
                );
            ''')
            
            # Migration: add time fields to exclusion_periods if needed
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(exclusion_periods)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'start_time' not in column_names:
                cursor.execute('ALTER TABLE exclusion_periods ADD COLUMN start_time TIME')
            if 'end_time' not in column_names:
                cursor.execute('ALTER TABLE exclusion_periods ADD COLUMN end_time TIME')
            
            # Migration: add employee_id and child_id to exclusion_periods if needed
            if 'employee_id' not in column_names:
                cursor.execute('ALTER TABLE exclusion_periods ADD COLUMN employee_id INTEGER REFERENCES employees(id)')
            if 'child_id' not in column_names:
                cursor.execute('ALTER TABLE exclusion_periods ADD COLUMN child_id INTEGER REFERENCES children(id)')
            
            # Migration: add hourly_rate to employees if needed
            cursor.execute("PRAGMA table_info(employees)")
            columns = cursor.fetchall()
            emp_column_names = [col[1] for col in columns]
            
            if 'hourly_rate' not in emp_column_names:
                cursor.execute('ALTER TABLE employees ADD COLUMN hourly_rate REAL')
            
            # Migration: add hidden to employees if needed
            if 'hidden' not in emp_column_names:
                cursor.execute('ALTER TABLE employees ADD COLUMN hidden BOOLEAN DEFAULT 0')

            # Migration: add employee_aliases table if needed
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='employee_aliases'
            """)
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE employee_aliases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        alias TEXT NOT NULL,
                        slug TEXT NOT NULL UNIQUE,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id)
                    )
                ''')

            # Migration: fix invalid CHECK on shifts and ensure indexes/constraints
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='shifts'")
            row = cursor.fetchone()
            shifts_sql = row[0] if row else ''

            needs_rebuild = False
            if 'CHECK (date(start_time) = date(end_time))' in shifts_sql:
                needs_rebuild = True

            # Rebuild shifts table if needed to remove invalid CHECK and add proper CHECK
            if needs_rebuild:
                cursor.execute('PRAGMA foreign_keys = OFF')
                cursor.execute('''
                    CREATE TABLE shifts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        child_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        service_code TEXT,
                        status TEXT,
                        is_imported BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id),
                        FOREIGN KEY (child_id) REFERENCES children(id),
                        CHECK (end_time > start_time)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO shifts_new (id, employee_id, child_id, date, start_time, end_time, service_code, status, is_imported, created_at)
                    SELECT id, employee_id, child_id, date, start_time, end_time, service_code, status, is_imported, created_at FROM shifts
                ''')
                cursor.execute('DROP TABLE shifts')
                cursor.execute('ALTER TABLE shifts_new RENAME TO shifts')
                cursor.execute('PRAGMA foreign_keys = ON')
                # Recreate helpful indexes after table rebuild
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_shift_employee_date ON shifts(employee_id, date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_shift_child_date ON shifts(child_id, date)')

            # Ensure unique index includes end_time
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name='idx_shift_unique'")
            idx = cursor.fetchone()
            if idx:
                idx_sql = idx[1] or ''
                if 'start_time, end_time' not in idx_sql:
                    cursor.execute('DROP INDEX IF EXISTS idx_shift_unique')
                    cursor.execute('CREATE UNIQUE INDEX idx_shift_unique ON shifts(employee_id, child_id, date, start_time, end_time)')
            else:
                cursor.execute('CREATE UNIQUE INDEX idx_shift_unique ON shifts(employee_id, child_id, date, start_time, end_time)')

            # Create overlap-preventing triggers for manual shifts (is_imported = 0)
            def ensure_trigger(name, sql):
                cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name = ?", (name,))
                if not cursor.fetchone():
                    cursor.execute(sql)

            ensure_trigger(
                'trg_shifts_no_overlap_employee_insert',
                '''
                CREATE TRIGGER trg_shifts_no_overlap_employee_insert
                BEFORE INSERT ON shifts
                WHEN NEW.is_imported = 0 AND EXISTS (
                    SELECT 1 FROM shifts s
                    WHERE s.date = NEW.date
                      AND s.employee_id = NEW.employee_id
                      AND NOT (NEW.end_time <= s.start_time OR NEW.start_time >= s.end_time)
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Conflicts with existing shift for employee');
                END;
                '''
            )

            ensure_trigger(
                'trg_shifts_no_overlap_child_insert',
                '''
                CREATE TRIGGER trg_shifts_no_overlap_child_insert
                BEFORE INSERT ON shifts
                WHEN NEW.is_imported = 0 AND EXISTS (
                    SELECT 1 FROM shifts s
                    WHERE s.date = NEW.date
                      AND s.child_id = NEW.child_id
                      AND NOT (NEW.end_time <= s.start_time OR NEW.start_time >= s.end_time)
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Conflicts with existing shift for child');
                END;
                '''
            )

            ensure_trigger(
                'trg_shifts_no_overlap_employee_update',
                '''
                CREATE TRIGGER trg_shifts_no_overlap_employee_update
                BEFORE UPDATE ON shifts
                WHEN NEW.is_imported = 0 AND EXISTS (
                    SELECT 1 FROM shifts s
                    WHERE s.date = NEW.date
                      AND s.employee_id = NEW.employee_id
                      AND s.id != OLD.id
                      AND NOT (NEW.end_time <= s.start_time OR NEW.start_time >= s.end_time)
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Conflicts with existing shift for employee');
                END;
                '''
            )

            ensure_trigger(
                'trg_shifts_no_overlap_child_update',
                '''
                CREATE TRIGGER trg_shifts_no_overlap_child_update
                BEFORE UPDATE ON shifts
                WHEN NEW.is_imported = 0 AND EXISTS (
                    SELECT 1 FROM shifts s
                    WHERE s.date = NEW.date
                      AND s.child_id = NEW.child_id
                      AND s.id != OLD.id
                      AND NOT (NEW.end_time <= s.start_time OR NEW.start_time >= s.end_time)
                )
                BEGIN
                    SELECT RAISE(ABORT, 'Conflicts with existing shift for child');
                END;
                '''
            )
            
            # Migration: rename max_hours_per_period to max_hours_per_week if needed
            cursor.execute("PRAGMA table_info(hour_limits)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'max_hours_per_period' in column_names and 'max_hours_per_week' not in column_names:
                # Create new table with updated schema
                cursor.execute('''
                    CREATE TABLE hour_limits_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        child_id INTEGER NOT NULL,
                        max_hours_per_week REAL NOT NULL,
                        alert_threshold REAL,
                        active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id),
                        FOREIGN KEY (child_id) REFERENCES children(id),
                        UNIQUE(employee_id, child_id)
                    );
                ''')
                
                # Copy data, dividing period limits by 2 to get weekly limits
                cursor.execute('''
                    INSERT INTO hour_limits_new (id, employee_id, child_id, max_hours_per_week, alert_threshold, active, created_at)
                    SELECT id, employee_id, child_id, max_hours_per_period/2.0, alert_threshold/2.0, active, created_at
                    FROM hour_limits;
                ''')
                
                # Drop old table and rename new one
                cursor.execute('DROP TABLE hour_limits')
                cursor.execute('ALTER TABLE hour_limits_new RENAME TO hour_limits')
            
            # Migration: Create budget tables if they don't exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='child_budgets'
            """)
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE child_budgets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        child_id INTEGER NOT NULL,
                        period_start DATE NOT NULL,
                        period_end DATE NOT NULL,
                        budget_amount REAL,
                        budget_hours REAL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (child_id) REFERENCES children(id),
                        UNIQUE(child_id, period_start, period_end)
                    )
                ''')
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='employee_rates'
            """)
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE employee_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        hourly_rate REAL NOT NULL,
                        effective_date DATE NOT NULL,
                        end_date DATE,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id)
                    )
                ''')
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='budget_allocations'
            """)
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE budget_allocations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        child_id INTEGER NOT NULL,
                        employee_id INTEGER NOT NULL,
                        period_id INTEGER NOT NULL,
                        allocated_hours REAL NOT NULL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (child_id) REFERENCES children(id),
                        FOREIGN KEY (employee_id) REFERENCES employees(id),
                        FOREIGN KEY (period_id) REFERENCES payroll_periods(id)
                    )
                ''')
    
    def execute(self, query, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
    
    def fetchone(self, query, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
    
    def fetchall(self, query, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def insert(self, query, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.lastrowid
