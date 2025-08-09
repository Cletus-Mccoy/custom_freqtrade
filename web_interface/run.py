#!/usr/bin/env python3
"""
FreqTrade Web Interface - Development Runner
Improved startup script with better error handling and Docker connection status
"""

import os
import sys
import logging
from pathlib import Path
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import flask
        import docker
        import yaml
        logging.info("✅ All required packages are available")
        return True
    except ImportError as e:
        logging.error(f"❌ Missing required package: {e}")
        logging.info("Please run: pip install -r requirements.txt")
        return False

def check_docker_status():
    """Check Docker availability without importing the main app"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        info = client.info()
        logging.info(f"✅ Docker connected - Version: {info.get('ServerVersion', 'Unknown')}")
        return True
    except Exception as e:
        logging.warning(f"⚠️  Docker connection issue: {e}")
        logging.info("   Web interface will still work for configuration management")
        return False

def main():
    parser = argparse.ArgumentParser(description='FreqTrade Web Interface Development Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-docker-check', action='store_true', help='Skip Docker connection check')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 FreqTrade Web Management Interface")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Docker status (unless skipped)
    if not args.no_docker_check:
        docker_ok = check_docker_status()
        if not docker_ok:
            print("\n⚠️  Note: Some Docker features may be limited")
    
    # Import and run the app
    try:
        from app import app
        
        print(f"\n🌐 Starting web server...")
        print(f"   Host: {args.host}")
        print(f"   Port: {args.port}")
        print(f"   Debug: {args.debug}")
        print(f"\n📱 Access the interface at:")
        print(f"   Local:    http://localhost:{args.port}")
        if args.host == '0.0.0.0':
            print(f"   Network:  http://192.168.1.5:{args.port}")  # Example IP
        print("\n🛑 Press Ctrl+C to stop the server")
        print("=" * 60)
        
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Web interface stopped")
    except Exception as e:
        logging.error(f"❌ Failed to start web interface: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
