#!/usr/bin/env python3

"""
Stock Analysis API Server
Run this script to start the FastAPI server
"""

import uvicorn
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    print("🚀 Starting Stock Analysis API Server")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("=" * 50)
    
    uvicorn.run(
        "src.share_insights_v1.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )