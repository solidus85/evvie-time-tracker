class EmployeeService:
    def __init__(self, db):
        self.db = db
    
    def _slugify(self, text):
        if not text:
            return ''
        import re
        s = text.strip().lower()
        # replace non-alphanumeric with single hyphen
        s = re.sub(r'[^a-z0-9]+', '-', s)
        s = re.sub(r'-{2,}', '-', s).strip('-')
        return s
    
    def get_all(self, active_only=False):
        query = "SELECT * FROM employees"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY friendly_name"
        return self.db.fetchall(query)
    
    def get_by_id(self, employee_id):
        return self.db.fetchone(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,)
        )
    
    def get_by_system_name(self, system_name):
        return self.db.fetchone(
            "SELECT * FROM employees WHERE system_name = ?",
            (system_name,)
        )
    
    def get_by_alias(self, alias):
        slug = self._slugify(alias)
        # First check alias table
        row = self.db.fetchone(
            """
            SELECT e.* FROM employee_aliases a
            JOIN employees e ON e.id = a.employee_id
            WHERE a.slug = ?
            """,
            (slug,)
        )
        if row:
            return row
        # Fallback: some existing employees might have system_name as non-slug
        # Try exact name, then slug of system_name
        emp = self.get_by_system_name(alias)
        if emp:
            return emp
        # Try find employee whose system_name slug matches
        # (scan limited set: order by created_at desc)
        candidates = self.db.fetchall("SELECT * FROM employees ORDER BY created_at DESC LIMIT 200")
        for cand in candidates:
            if self._slugify(cand['system_name']) == slug:
                return cand
        return None
    
    def ensure_alias(self, employee_id, alias, source=None):
        slug = self._slugify(alias)
        if not slug:
            return
        existing = self.db.fetchone("SELECT id FROM employee_aliases WHERE slug = ?", (slug,))
        if existing:
            return
        self.db.insert(
            "INSERT INTO employee_aliases (employee_id, alias, slug, source) VALUES (?, ?, ?, ?)",
            (employee_id, alias, slug, source)
        )
    
    def create(self, friendly_name, system_name, active=True, hidden=False):
        existing = self.get_by_system_name(system_name)
        if existing:
            raise ValueError(f"Employee with system name '{system_name}' already exists")
        
        employee_id = self.db.insert(
            "INSERT INTO employees (friendly_name, system_name, active, hidden) VALUES (?, ?, ?, ?)",
            (friendly_name, system_name, active, hidden)
        )
        # Ensure the friendly name is also recorded as an alias if it differs
        try:
            if friendly_name != system_name:
                self.ensure_alias(employee_id, friendly_name, source='create')
        except Exception:
            pass
        return employee_id
    
    def update(self, employee_id, data):
        employee = self.get_by_id(employee_id)
        if not employee:
            return False
        
        updates = []
        params = []
        
        if 'friendly_name' in data:
            updates.append("friendly_name = ?")
            params.append(data['friendly_name'])
        
        if 'system_name' in data:
            if data['system_name'] != employee['system_name']:
                existing = self.get_by_system_name(data['system_name'])
                if existing:
                    raise ValueError(f"Employee with system name '{data['system_name']}' already exists")
            updates.append("system_name = ?")
            params.append(data['system_name'])
        
        if 'active' in data:
            updates.append("active = ?")
            params.append(data['active'])
        
        if 'hidden' in data:
            updates.append("hidden = ?")
            params.append(data['hidden'])
        
        if not updates:
            return True
        
        params.append(employee_id)
        query = f"UPDATE employees SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, params)
        return True
    
    def deactivate(self, employee_id):
        employee = self.get_by_id(employee_id)
        if not employee:
            return False
        
        self.db.execute(
            "UPDATE employees SET active = 0 WHERE id = ?",
            (employee_id,)
        )
        return True
