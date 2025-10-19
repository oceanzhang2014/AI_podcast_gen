#!/usr/bin/env python3
"""
Production startup script for AI Podcast Generator
"""

import os
import sys
from pathlib import Path

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

def main():
    """Start the application in production mode."""
    print("Starting AI Podcast Generator in Production Mode")
    print("=" * 60)

    # Check CUDA
    try:
        import torch
        print(f"[OK] PyTorch {torch.__version__}")
        print(f"    CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"    GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("[ERROR] PyTorch not found")

    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("[OK] FFmpeg is available")
        else:
            print("[ERROR] FFmpeg not available")
    except Exception:
        print("[ERROR] FFmpeg not available")

    # Import and start application
    try:
        from app import app, logger
        logger.info("=== PRODUCTION MODE STARTUP ===")

        # Use waitress for production
        from waitress import serve

        print("\nStarting production server with Waitress...")
        print("Host: 0.0.0.0, Port: 5000")
        print("Access URLs:")
        print("  - Local: http://127.0.0.1:5000")
        print("  - Network: http://192.168.0.4:5000")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60)

        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=8,
            connection_limit=1000,
            max_request_body_size=1073741824
        )

    except KeyboardInterrupt:
        print("\nServer stopped by user")
        logger.info("=== PRODUCTION MODE SHUTDOWN ===")
    except Exception as e:
        print(f"\nFailed to start server: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()