#!/usr/bin/env python3
"""
Database Dashboard Runner
Run the new database-driven stock analysis dashboard
"""

import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.share_insights_v1.dashboard.database_dashboard import main

if __name__ == "__main__":
    main()