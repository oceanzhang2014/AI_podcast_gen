#!/usr/bin/env python3
"""
Startup script for AI Podcast Generator

Run this script to start the Flask development server.
Usage: python run.py
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point for the application."""
    try:
        import app

        print("=" * 60)
        print("AI Podcast Generator")
        print("=" * 60)
        print(f"Debug mode: {app.app.config['DEBUG']}")
        print(f"Upload folder: {app.app.config['UPLOAD_FOLDER']}")
        print(f"Secret key: {'SET' if app.app.config['SECRET_KEY'] else 'NOT SET'}")
        print("=" * 60)
        print("\nStarting Flask development server...")
        print(f"Server will be available at: http://{app.HOST}:{app.PORT}")
        print("Press Ctrl+C to stop the server\n")

        # Run the Flask application
        app.app.run(
            host=app.HOST,
            port=app.PORT,
            debug=app.DEBUG,
            use_reloader=app.DEBUG  # Enable auto-reload in debug mode
        )

    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()