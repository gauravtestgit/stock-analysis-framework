#!/usr/bin/env python3

"""
Stock Analysis Dashboard Launcher
Run this script to start the Streamlit dashboard
"""

import subprocess
import sys
import os

def run_dashboard():
    """Launch the Streamlit dashboard"""
    
    print("🚀 Starting Stock Analysis Dashboard")
    print("📊 Dashboard will open at: http://localhost:8501")
    print("🔍 Make sure the API server is running at: http://localhost:8000")
    print("=" * 60)
    
    # Change to dashboard directory
    dashboard_dir = os.path.join("src", "share_insights_v1", "dashboard")
    
    # Run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        "main_dashboard.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ]
    
    try:
        subprocess.run(cmd, cwd=dashboard_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    run_dashboard()