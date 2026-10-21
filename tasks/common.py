"""Shared utilities for development tasks."""

import subprocess
import sys
from pathlib import Path

PRJ_ROOT = Path(__file__).resolve().parent.parent


def run_command(*args, **kwargs):
    """Run a subprocess command safely inside the project root."""
    # Default to project root context and fail-fast behavior
    kwargs.setdefault('cwd', PRJ_ROOT)
    kwargs.setdefault('check', True)

    # Format the command for clean logging output
    cmd_arg = args[0] if args else None
    if isinstance(cmd_arg, (list, tuple)):
        display_cmd = ' '.join(str(x) for x in cmd_arg)
    elif isinstance(cmd_arg, str):
        display_cmd = cmd_arg
    else:
        display_cmd = ' '.join(str(arg) for arg in args)

    print(f'\n[Run] {display_cmd}')

    try:
        return subprocess.run(*args, check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        print(f'[Error] Command failed with exit code {e.returncode}')
        if kwargs.get('capture_output') and e.stderr:
            print(e.stderr)
        sys.exit(1)
