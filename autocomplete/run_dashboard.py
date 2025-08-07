#!/usr/bin/env python3
"""
Dashboard launcher script for POI Evaluation Dashboard
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting POI Evaluation Dashboard...")
    print("Make sure you have installed the required dependencies:")
    print("pip install -r requirements_dashboard.txt")
    print("\nDashboard will open in your default web browser.")
    print("Press Ctrl+C to stop the server.\n")
    
    # Change to the directory containing dashboard.py
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(dashboard_dir)
    
    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "src/dashboard.py",
        "--server.port", "8501",
        "--server.address", "localhost"
    ])

if __name__ == "__main__":
    main()
