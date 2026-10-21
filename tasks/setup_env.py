"""Standard environment setup using uv. venv activation is not needed."""

from common import run_command


def main():	
	commands  = [
		"uv venv",
		"uv pip install -e .",
		"uv sync"
	]
	
	for cmd in commands:
		run_command(cmd, shell=True)

	print("\nAll environment setup steps completed successfully!")

if __name__ == "__main__":
	main()