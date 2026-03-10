"""Helper script to run alembic and capture full output."""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
result = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    capture_output=True, text=True
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
