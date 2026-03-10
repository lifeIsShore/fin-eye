"""Attempt to create the FastAPI app and catch any startup AssertionError."""
import traceback
import sys

try:
    # This mimics what uvicorn does
    from app.main import app
    print("SUCCESS: app created")
    print(f"Routes: {[r.path for r in app.routes[:5]]}")
except AssertionError as e:
    print(f"ASSERTION ERROR: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"OTHER ERROR ({type(e).__name__}): {e}")
    traceback.print_exc()
