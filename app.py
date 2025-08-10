from flask import Flask, render_template, jsonify
from flask_cors import CORS
from config import Config
from database import Database
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    db = Database(app.config['DATABASE'])
    app.db = db
    
    from routes import employees, children, shifts, payroll, imports, exports, config
    
    app.register_blueprint(employees.bp, url_prefix='/api/employees')
    app.register_blueprint(children.bp, url_prefix='/api/children')
    app.register_blueprint(shifts.bp, url_prefix='/api/shifts')
    app.register_blueprint(payroll.bp, url_prefix='/api/payroll')
    app.register_blueprint(imports.bp, url_prefix='/api/import')
    app.register_blueprint(exports.bp, url_prefix='/api/export')
    app.register_blueprint(config.bp, url_prefix='/api/config')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'})
    
    @app.route('/favicon.ico')
    def favicon():
        return '', 204
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])