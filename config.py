import os

class Config:
    SECRET_KEY_FILE = os.environ.get('SECRET_KEY_FILE') or 'secret.key'
    
    @property
    def SECRET_KEY(self):
        if os.path.exists(self.SECRET_KEY_FILE):
            with open(self.SECRET_KEY_FILE, 'r') as f:
                return f.read().strip()
        else:
            import secrets
            key = secrets.token_hex(32)
            with open(self.SECRET_KEY_FILE, 'w') as f:
                f.write(key)
            return key
    
    DATABASE = 'evvie_time_tracker.db'
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000
    
    TIMEZONE = 'America/Chicago'
    DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%I:%M %p'
    DATETIME_FORMAT = '%Y-%m-%d %I:%M %p'
    
    MAX_CSV_SIZE_MB = 10
    ALLOWED_CSV_EXTENSIONS = {'csv'}
    
    PDF_PAGE_SIZE = 'LETTER'
    PDF_FONT_SIZE = 10