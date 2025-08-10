class ConfigService:
    def __init__(self, db):
        self.db = db
    
    def get_all_hour_limits(self, active_only=False):
        query = """
            SELECT h.*, e.friendly_name as employee_name, c.name as child_name
            FROM hour_limits h
            JOIN employees e ON h.employee_id = e.id
            JOIN children c ON h.child_id = c.id
        """
        if active_only:
            query += " WHERE h.active = 1"
        query += " ORDER BY e.friendly_name, c.name"
        return self.db.fetchall(query)
    
    def get_hour_limit(self, employee_id, child_id):
        return self.db.fetchone(
            """SELECT * FROM hour_limits
               WHERE employee_id = ? AND child_id = ? AND active = 1""",
            (employee_id, child_id)
        )
    
    def create_hour_limit(self, employee_id, child_id, max_hours_per_period, alert_threshold=None):
        existing = self.get_hour_limit(employee_id, child_id)
        if existing:
            raise ValueError("Hour limit already exists for this employee/child pair")
        
        if alert_threshold and alert_threshold >= max_hours_per_period:
            raise ValueError("Alert threshold must be less than max hours")
        
        return self.db.insert(
            """INSERT INTO hour_limits (employee_id, child_id, max_hours_per_period, alert_threshold)
               VALUES (?, ?, ?, ?)""",
            (employee_id, child_id, max_hours_per_period, alert_threshold)
        )
    
    def update_hour_limit(self, limit_id, data):
        limit = self.db.fetchone(
            "SELECT * FROM hour_limits WHERE id = ?",
            (limit_id,)
        )
        
        if not limit:
            return False
        
        updates = []
        params = []
        
        if 'max_hours_per_period' in data:
            updates.append("max_hours_per_period = ?")
            params.append(data['max_hours_per_period'])
        
        if 'alert_threshold' in data:
            if data['alert_threshold'] and 'max_hours_per_period' in data:
                if data['alert_threshold'] >= data['max_hours_per_period']:
                    raise ValueError("Alert threshold must be less than max hours")
            elif data['alert_threshold'] and data['alert_threshold'] >= limit['max_hours_per_period']:
                raise ValueError("Alert threshold must be less than max hours")
            
            updates.append("alert_threshold = ?")
            params.append(data['alert_threshold'])
        
        if 'active' in data:
            updates.append("active = ?")
            params.append(data['active'])
        
        if not updates:
            return True
        
        params.append(limit_id)
        query = f"UPDATE hour_limits SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, params)
        return True
    
    def deactivate_hour_limit(self, limit_id):
        limit = self.db.fetchone(
            "SELECT * FROM hour_limits WHERE id = ?",
            (limit_id,)
        )
        
        if not limit:
            return False
        
        self.db.execute(
            "UPDATE hour_limits SET active = 0 WHERE id = ?",
            (limit_id,)
        )
        return True
    
    def get_app_settings(self):
        settings = self.db.fetchall("SELECT * FROM app_config")
        return {setting['key']: setting['value'] for setting in settings}
    
    def update_app_settings(self, settings):
        for key, value in settings.items():
            self.db.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                (key, value)
            )
    
    def get_setting(self, key):
        result = self.db.fetchone(
            "SELECT value FROM app_config WHERE key = ?",
            (key,)
        )
        return result['value'] if result else None
    
    def set_setting(self, key, value):
        self.db.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            (key, value)
        )