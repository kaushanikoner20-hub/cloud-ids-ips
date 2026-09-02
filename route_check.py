import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("Successfully imported app")
    print("\nRegistered Routes:")
    for route in app.routes:
        print(f"Method: {route.methods} | Path: {route.path}")
except Exception as e:
    print(f"Error: {e}")
