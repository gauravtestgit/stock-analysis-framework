#!/usr/bin/env python3
"""
UI 1.0 Runner Script
Run the next-generation stock analysis dashboard
"""

import subprocess
import sys
import os

def run_dashboard():
    """Run the UI 1.0 dashboard"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    # Run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", "8502",  # Different port from original dashboard
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false"
    ]
    
    print("🚀 Starting Stock Analysis UI 1.0...")
    print(f"📊 Dashboard will be available at: http://localhost:8502")
    print("🔄 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        subprocess.run(cmd, cwd=script_dir)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    run_dashboard()