#!/usr/bin/env python3
"""
Optimized startup script for Lagos Accessibility Dashboard
This script provides performance optimizations and pre-warming of caches.
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

def setup_environment():
    """Setup optimal environment variables for Streamlit performance."""
    # Streamlit performance optimizations
    os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "200"  # MB
    os.environ["STREAMLIT_SERVER_MAX_MESSAGE_SIZE"] = "200"  # MB
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_CLIENT_TOOLBAR_MODE"] = "minimal"
    
    # Python optimizations
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["PYTHONHASHSEED"] = "0"  # For reproducible results
    
    print("✅ Environment optimized for performance")

def check_data_files():
    """Check if required data files exist."""
    data_dir = Path("Data")
    required_files = [
        "TAZ.geojson",
        "Base Scenario.xlsx", 
        "Lagos_Node.xlsx",
        "LGAs.geojson"
    ]
    
    missing_files = []
    for file in required_files:
        if not (data_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing data files: {', '.join(missing_files)}")
        print("Please ensure all required data files are in the Data/ directory")
        return False
    
    print("✅ All required data files found")
    return True

def run_dashboard(port=8501, debug=False):
    """Run the dashboard with optimized settings."""
    
    # Base command
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--client.toolbarMode", "minimal"
    ]
    
    if debug:
        cmd.extend(["--logger.level", "debug"])
    else:
        cmd.extend(["--logger.level", "error"])
    
    print(f"🚀 Starting Lagos Accessibility Dashboard on port {port}")
    print("💡 Tip: The first load may take 15-30 seconds to cache data files")
    print("⚡ Subsequent loads will be much faster!")
    print(f"🌐 Open your browser to: http://localhost:{port}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Run Lagos Accessibility Dashboard with optimizations")
    parser.add_argument("--port", type=int, default=8501, help="Port to run the dashboard on (default: 8501)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--check-only", action="store_true", help="Only check requirements, don't start dashboard")
    
    args = parser.parse_args()
    
    print("🗺️  Lagos Accessibility Dashboard - Optimized Launcher")
    print("=" * 50)
    
    # Setup environment
    setup_environment()
    
    # Check data files
    if not check_data_files():
        sys.exit(1)
    
    if args.check_only:
        print("✅ All checks passed! You can now run the dashboard.")
        return
    
    # Run the dashboard
    run_dashboard(port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
