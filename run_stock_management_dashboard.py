#!/usr/bin/env python3

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# Import the main function from the dashboard
from src.share_insights_v1.dashboard.stock_management_dashboard import main

if __name__ == "__main__":
    main()