from flask import Flask, render_template, jsonify
from flask_cors import CORS
from config import Config
from database import Database
import os
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.logger.setLevel(logging.INFO)
    
    db = Database(app.config['DATABASE'])
    app.db = db
    
    from routes import employees, children, shifts, payroll, imports, exports, config, budget, forecast
    
    app.register_blueprint(employees.bp, url_prefix='/api/employees')
    app.register_blueprint(children.bp, url_prefix='/api/children')
    app.register_blueprint(shifts.bp, url_prefix='/api/shifts')
    app.register_blueprint(payroll.bp, url_prefix='/api/payroll')
    app.register_blueprint(imports.bp, url_prefix='/api/import')
    app.register_blueprint(exports.bp, url_prefix='/api/export')
    app.register_blueprint(config.bp, url_prefix='/api/config')
    app.register_blueprint(budget.bp, url_prefix='/api/budget')
    app.register_blueprint(forecast.bp, url_prefix='/api/forecast')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'})
    
    @app.route('/favicon.ico')
    def favicon():
        # Serve ICO favicon (multi-size, transparent) if present; fallback to PNG
        try:
            return app.send_static_file('favicon.ico')
        except Exception:
            return app.send_static_file('favicon.png')
    
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
