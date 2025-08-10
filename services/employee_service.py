class EmployeeService:
    def __init__(self, db):
        self.db = db
    
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
    
    def create(self, friendly_name, system_name, active=True):
        existing = self.get_by_system_name(system_name)
        if existing:
            raise ValueError(f"Employee with system name '{system_name}' already exists")
        
        return self.db.insert(
            "INSERT INTO employees (friendly_name, system_name, active) VALUES (?, ?, ?)",
            (friendly_name, system_name, active)
        )
    
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