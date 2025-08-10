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
                    CHECK (date(start_time) = date(end_time))
                );
                
                CREATE UNIQUE INDEX IF NOT EXISTS idx_shift_unique 
                ON shifts(employee_id, child_id, date, start_time);
                
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
                    reason TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            ''')
            
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