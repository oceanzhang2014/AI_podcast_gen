#!/usr/bin/env python3
"""
Production startup script for AI Podcast Generator

This script sets up production environment variables and starts the application
using a production WSGI server.
"""

import os
import sys
from pathlib import Path

# Set production environment variables
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', 'False')
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Start the application in production mode."""
    print("Starting AI Podcast Generator in Production Mode")
    print("=" * 60)

    # Verify CUDA and FFmpeg availability
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__} with CUDA: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            print(f"   CUDA Version: {torch.version.cuda}")
    except ImportError:
        print("❌ PyTorch not found")

    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
        else:
            print("❌ FFmpeg not found")
    except FileNotFoundError:
        print("❌ FFmpeg not found")

    # Import and start the application
    try:
        from app import app, logger

        # Log production start
        logger.info("=== PRODUCTION MODE STARTUP ===")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Working Directory: {os.getcwd()}")
        logger.info(f"Environment: Production")

        # Use waitress as production server (Windows compatible)
        from waitress import serve

        print("\n🌐 Starting production server...")
        print("   Server: Waitress (Production WSGI)")
        print("   Port: 5000")
        print("   Host: 0.0.0.0 (All interfaces)")
        print("   Access URLs:")
        print("     - Local: http://127.0.0.1:5000")
        print("     - Network: http://192.168.0.4:5000")
        print("\n📝 Logs are being written to: podcast_generation_development.log")
        print("⚠️  Press Ctrl+C to stop the server")
        print("=" * 60)

        # Configure waitress for production
        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=8,  # Number of worker threads
            connection_limit=1000,  # Maximum connections
            cleanup_interval=10,  # Cleanup interval
            channel_timeout=120,  # Channel timeout
            max_request_body_size=1073741824,  # 1GB max request size
            send_bytes=1024 * 1024,  # Buffer size
        )

    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        logger.info("=== PRODUCTION MODE SHUTDOWN ===")
    except Exception as e:
        print(f"\n❌ Failed to start production server: {str(e)}")
        logger.error(f"Production startup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()