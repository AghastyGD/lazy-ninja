import subprocess
import sys
import os


def run_cli_command(args: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "lazy_ninja.cli.client_generator"] + args,
        capture_output=True,
        text=True, 
        env=env
    )
    

def test_help_command():
    result = run_cli_command(["--help"])
    assert result.returncode == 0
    assert "Lazy Ninja CLI" in result.stdout
    assert "generate-client" in result.stdout

    
def test_missing_required_arguments():
    result = run_cli_command(["generate-client", "typescript"])
    assert result.returncode != 0
    assert "--settings" in result.stderr
    
    
def test_invalid_language():
    result = run_cli_command(["generate-client", "invalid", "--settings", "myproject.settings"])
    assert result.returncode == 2
    assert "invalid choice: 'invalid'" in result.stderr
    assert "choose from" in result.stderr


def test_invalid_command():
    result = run_cli_command(["invalid-command"])
    assert result.returncode != 0
    assert "invalid choice" in result.stderr.lower()
