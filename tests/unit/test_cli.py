import subprocess
import sys


def test_help():
    result = subprocess.run([sys.executable, "-m", "android_stack_skills.cli", "--help"], capture_output=True)
    assert result.returncode == 0
