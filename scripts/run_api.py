"""
Test API server startup and basic endpoints.

Responsibility: API testing
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uvicorn
from api.main import app


if __name__ == "__main__":
    print("🚀 Starting TrueCivic API Server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 Swagger docs at: http://localhost:8000/docs")
    print("🔍 ReDoc at: http://localhost:8000/redoc")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
