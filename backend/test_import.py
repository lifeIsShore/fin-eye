"""Test if app.main can be imported without errors."""
import sys
import traceback

try:
    import app.main
    print("SUCCESS: app.main imported successfully")
except Exception as e:
    print(f"IMPORT ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
