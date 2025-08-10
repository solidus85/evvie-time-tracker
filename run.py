#!/usr/bin/env python3
import sys
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    print("=" * 50)
    print("Evvie Time Tracker")
    print("=" * 50)
    print(f"Starting server at http://{app.config['HOST']}:{app.config['PORT']}")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        app.run(
            host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG']
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)