class ChildService:
    def __init__(self, db):
        self.db = db
    
    def get_all(self, active_only=False):
        query = "SELECT * FROM children"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name"
        return self.db.fetchall(query)
    
    def get_by_id(self, child_id):
        return self.db.fetchone(
            "SELECT * FROM children WHERE id = ?",
            (child_id,)
        )
    
    def get_by_code(self, code):
        return self.db.fetchone(
            "SELECT * FROM children WHERE code = ?",
            (code,)
        )
    
    def create(self, name, code, active=True):
        existing = self.get_by_code(code)
        if existing:
            raise ValueError(f"Child with code '{code}' already exists")
        
        return self.db.insert(
            "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
            (name, code, active)
        )
    
    def update(self, child_id, data):
        child = self.get_by_id(child_id)
        if not child:
            return False
        
        updates = []
        params = []
        
        if 'name' in data:
            updates.append("name = ?")
            params.append(data['name'])
        
        if 'code' in data:
            if data['code'] != child['code']:
                existing = self.get_by_code(data['code'])
                if existing:
                    raise ValueError(f"Child with code '{data['code']}' already exists")
            updates.append("code = ?")
            params.append(data['code'])
        
        if 'active' in data:
            updates.append("active = ?")
            params.append(data['active'])
        
        if not updates:
            return True
        
        params.append(child_id)
        query = f"UPDATE children SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(query, params)
        return True
    
    def deactivate(self, child_id):
        child = self.get_by_id(child_id)
        if not child:
            return False
        
        self.db.execute(
            "UPDATE children SET active = 0 WHERE id = ?",
            (child_id,)
        )
        return True