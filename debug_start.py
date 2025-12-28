import sys
import subprocess

# Run the command and capture output
result = subprocess.run(
    [sys.executable, "start_mindstack_app.py"],
    cwd=r"c:\Code\MindStack\newmindstack",
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
