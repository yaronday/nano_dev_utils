"""Build and upload the package to PyPI or TestPyPI."""
from common import run_command


def run(target: str = "pypi") -> None:
    repo_flag = f"--repository {target}" if target != "pypi" else ""
    
    commands = [
        "uv add --dev build twine",
        "uv build",
        f"twine upload {repo_flag} dist/*".strip(),
    ]

    for cmd in commands:
        run_command(cmd)

    print(f"\nPackage successfully built and uploaded to {target}!")


if __name__ == "__main__":
	# run()  # pypi 
    run("testpypi")