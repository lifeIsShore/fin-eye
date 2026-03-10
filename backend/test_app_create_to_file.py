"""Write the traceback to a file cleanly."""
import traceback
import sys

try:
    from app.main import app
    print("SUCCESS")
except Exception as e:
    with open("app_startup_error.txt", "w") as f:
        f.write(f"{type(e).__name__}: {e}\n\n")
        traceback.print_exc(file=f)
    print("FAILED - check app_startup_error.txt")
