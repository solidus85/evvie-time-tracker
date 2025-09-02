import os
import secrets

def get_or_create_secret_key():
    secret_key_file = os.environ.get('SECRET_KEY_FILE') or 'secret.key'
    if os.path.exists(secret_key_file):
        with open(secret_key_file, 'r') as f:
            return f.read().strip()
    else:
        key = secrets.token_hex(32)
        with open(secret_key_file, 'w') as f:
            f.write(key)
        return key

class Config:
    SECRET_KEY = get_or_create_secret_key()
    
    DATABASE = 'evvie_time_tracker.db'
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 8040
    
    TIMEZONE = 'America/Chicago'
    DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%I:%M %p'
    DATETIME_FORMAT = '%Y-%m-%d %I:%M %p'
    
    MAX_CSV_SIZE_MB = 10
    ALLOWED_CSV_EXTENSIONS = {'csv'}
    
    PDF_PAGE_SIZE = 'LETTER'
    PDF_FONT_SIZE = 10